"""Envoltura de AutoDock Vina (subprocess) y preparación de ligandos.

Módulo puro de Python (sin imports de Qt) para poder probarse/usarse de
forma independiente de la interfaz gráfica. Todas las funciones públicas
están diseñadas para NUNCA lanzar una excepción no controlada: en su lugar
devuelven una tupla/objeto con un mensaje de error claro en español cuando
falta una dependencia externa (binario de Vina, RDKit, meeko) o cuando los
datos de entrada son inválidos.

NOTA IMPORTANTE: en el entorno de desarrollo de este módulo no se dispuso de
acceso a un binario de AutoDock Vina ni a los paquetes RDKit-conformer/meeko
para verificar una ejecución de extremo a extremo. El código se escribió con
cuidado siguiendo la interfaz de línea de comandos documentada de Vina y las
APIs públicas de RDKit/meeko, pero se recomienda al usuario final probarlo
con sus propios datos y reportar cualquier discrepancia.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DockingPose:
    rank: int
    affinity_kcal_mol: float
    rmsd_lb: float
    rmsd_ub: float


@dataclass
class DockingResult:
    success: bool
    error: str
    poses: list[DockingPose] = field(default_factory=list)
    output_pdbqt_path: str = ""
    log_text: str = ""


def find_vina_executable(custom_path: Optional[str] = None) -> Optional[str]:
    """Busca el ejecutable de AutoDock Vina.

    Primero usa `custom_path` si se proporciona y existe, luego busca
    `vina`, `autodock_vina` y `vina.exe` en el PATH del sistema.
    """
    if custom_path and Path(custom_path).is_file():
        return custom_path
    for name in ("vina", "autodock_vina", "vina.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def prepare_ligand_from_smiles(smiles: str, output_pdbqt_path: str) -> tuple[bool, str]:
    """Genera un confórmero 3D con RDKit y prepara el ligando en PDBQT con meeko.

    Devuelve (éxito, mensaje_de_error_o_vacío). Captura cualquier problema de
    importación o de API (las APIs de RDKit/meeko han cambiado de versión a
    versión) para que nunca se propague una excepción sin control hacia la UI.
    """
    smiles = (smiles or "").strip()
    if not smiles:
        return False, "Debes ingresar una cadena SMILES para el ligando."

    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        return False, ("RDKit no está instalado. Instala el paquete 'rdkit' para "
                        "generar la geometría 3D del ligando.")
    except Exception as e:
        return False, f"Error inesperado al importar RDKit: {e}"

    try:
        meeko_module = None
        try:
            from meeko import MoleculePreparation, PDBQTWriterLegacy
            meeko_module = "legacy"
        except ImportError:
            # Algunas versiones de meeko no exponen PDBQTWriterLegacy por
            # separado; MoleculePreparation.write_pdbqt_string() es la API
            # alternativa usada en versiones anteriores/posteriores.
            from meeko import MoleculePreparation
            meeko_module = "write_method"
    except ImportError:
        return False, ("El paquete 'meeko' no está instalado. Instálalo con "
                        "'pip install meeko' para preparar el ligando en formato PDBQT.")
    except Exception as e:
        return False, f"Error inesperado al importar meeko: {e}"

    try:
        mol = Chem.MolFromSmiles(smiles)
    except Exception as e:
        return False, f"Error al interpretar el SMILES: {e}"
    if mol is None:
        return False, "SMILES de ligando inválido."

    try:
        mol = Chem.AddHs(mol)
        embed_result = AllChem.EmbedMolecule(mol, randomSeed=42, useRandomCoords=True)
        if embed_result != 0:
            return False, "No se pudo generar una geometría 3D para el ligando."
        try:
            AllChem.MMFFOptimizeMolecule(mol)
        except Exception:
            # La optimización MMFF es opcional; si falla (p. ej. parámetros
            # de campo de fuerza no disponibles para algún átomo), se
            # continúa con la geometría embebida sin optimizar.
            pass
    except Exception as e:
        return False, f"Error al generar la geometría 3D del ligando: {e}"

    try:
        if meeko_module == "legacy":
            preparator = MoleculePreparation()
            mol_setups = preparator.prepare(mol)
            pdbqt_string = PDBQTWriterLegacy.write_string(mol_setups[0])[0]
        else:
            preparator = MoleculePreparation()
            mol_setups = preparator.prepare(mol)
            pdbqt_string = preparator.write_pdbqt_string(mol_setups[0])
    except Exception as e:
        return False, (f"Error al preparar el ligando con meeko: {e}\n"
                        "(La API de meeko varía entre versiones; verifica que la "
                        "versión instalada sea compatible con meeko>=0.5.0.)")

    try:
        Path(output_pdbqt_path).write_text(pdbqt_string)
    except Exception as e:
        return False, f"No se pudo escribir el archivo PDBQT de salida: {e}"

    return True, ""


def validate_receptor_pdbqt(path: str) -> tuple[bool, str]:
    """Valida que el archivo de receptor exista y tenga extensión .pdbqt.

    No realiza conversión automática: el usuario debe proporcionar un
    receptor ya preparado (con AutoDockTools/ADFR/Meeko), ya que la
    preparación de receptores (adición de hidrógenos polares, asignación de
    cargas, tipado de átomos) requiere herramientas externas no garantizadas
    en este entorno.
    """
    if not path:
        return False, "Debes seleccionar un archivo de receptor (.pdbqt)."
    p = Path(path)
    if not p.is_file():
        return False, f"El archivo de receptor no existe: {path}"
    if p.suffix.lower() != ".pdbqt":
        return False, ("El receptor debe estar en formato .pdbqt ya preparado "
                        "(usa AutoDockTools, ADFR o Meeko para convertirlo desde "
                        ".pdb antes de cargarlo aquí).")
    return True, ""


def run_vina_docking(
    receptor_pdbqt: str,
    ligand_pdbqt: str,
    output_pdbqt: str,
    center: tuple[float, float, float],
    box_size: tuple[float, float, float],
    exhaustiveness: int = 8,
    num_modes: int = 9,
    vina_executable: Optional[str] = None,
) -> DockingResult:
    """Ejecuta AutoDock Vina vía subprocess y parsea las poses resultantes."""
    vina_path = find_vina_executable(vina_executable)
    if vina_path is None:
        return DockingResult(
            success=False,
            error=("No se encontró el ejecutable de AutoDock Vina. Instálalo y "
                   "asegúrate de que esté en el PATH del sistema, o especifica "
                   "la ruta completa al ejecutable en el panel."),
        )

    ok, msg = validate_receptor_pdbqt(receptor_pdbqt)
    if not ok:
        return DockingResult(success=False, error=msg)
    if not ligand_pdbqt or not Path(ligand_pdbqt).is_file():
        return DockingResult(success=False,
                              error=f"El archivo de ligando no existe: {ligand_pdbqt}")

    cmd = [
        vina_path,
        "--receptor", receptor_pdbqt,
        "--ligand", ligand_pdbqt,
        "--out", output_pdbqt,
        "--center_x", str(center[0]), "--center_y", str(center[1]), "--center_z", str(center[2]),
        "--size_x", str(box_size[0]), "--size_y", str(box_size[1]), "--size_z", str(box_size[2]),
        "--exhaustiveness", str(exhaustiveness),
        "--num_modes", str(num_modes),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        return DockingResult(success=False,
                              error=f"No se pudo ejecutar el binario de Vina en: {vina_path}")
    except subprocess.TimeoutExpired:
        return DockingResult(success=False,
                              error="El docking superó el tiempo límite de 600 segundos.")
    except Exception as e:
        return DockingResult(success=False, error=f"Error inesperado al ejecutar Vina: {e}")

    if proc.returncode != 0:
        return DockingResult(
            success=False,
            error=f"Vina terminó con error (código {proc.returncode}):\n{proc.stderr or proc.stdout}",
            log_text=(proc.stdout or "") + (proc.stderr or ""),
        )

    poses = parse_vina_log(proc.stdout)
    return DockingResult(success=True, error="", poses=poses,
                          output_pdbqt_path=output_pdbqt, log_text=proc.stdout)


def parse_vina_log(log_text: str) -> list[DockingPose]:
    """Extrae la tabla de poses (rank, afinidad, RMSD l.b./u.b.) de la salida
    estándar de texto de AutoDock Vina.

    El formato típico de la tabla de Vina es:

        mode |   affinity | dist from best mode
             | (kcal/mol) | rmsd l.b.| rmsd u.b.
        -----+------------+----------+----------
           1       -7.1      0.000      0.000
           2       -6.8      1.234      2.456
           ...

    Se buscan líneas cuyo primer token sea un entero (el rank) seguido de al
    menos 3 valores numéricos.
    """
    poses: list[DockingPose] = []
    if not log_text:
        return poses
    for line in log_text.splitlines():
        stripped = line.strip()
        if not stripped or not stripped[0].isdigit():
            continue
        parts = stripped.split()
        if len(parts) >= 4:
            try:
                rank = int(parts[0])
                affinity = float(parts[1])
                rmsd_lb = float(parts[2])
                rmsd_ub = float(parts[3])
                poses.append(DockingPose(rank, affinity, rmsd_lb, rmsd_ub))
            except ValueError:
                continue
    return poses
