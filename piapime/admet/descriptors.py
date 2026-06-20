"""
Descriptores ADMET ligeros basados únicamente en RDKit.

Calcula propiedades fisicoquímicas y reglas heurísticas clásicas
(Lipinski, Veber, Egan) sin recurrir a modelos de aprendizaje automático
ni a llamadas de red (PubChem/ChEMBL). Esta es una elección de diseño
explícita del módulo: todo el cálculo es local y offline. Las notas de
absorción, barrera hematoencefálica (BBB) y riesgo de sustrato de P-gp
son heurísticas simples basadas en reglas de corte fisicoquímicas, NO
predicciones validadas por modelos de machine learning — deben
interpretarse únicamente como una primera aproximación orientativa.
"""

from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors


@dataclass
class ADMETResult:
    """Contenedor de descriptores y reglas ADMET calculados a partir de un SMILES."""

    valid: bool
    error: str
    mol_formula: str
    mw: float = 0.0
    logp: float = 0.0
    tpsa: float = 0.0
    hbd: int = 0
    hba: int = 0
    rotatable_bonds: int = 0
    aromatic_rings: int = 0
    heavy_atoms: int = 0
    fraction_csp3: float = 0.0
    molar_refractivity: float = 0.0
    lipinski_violations: int = 0
    lipinski_pass: bool = False
    veber_pass: bool = False
    egan_pass: bool = False
    absorption_note: str = ""
    bbb_note: str = ""
    pgp_substrate_risk: str = ""


def compute_admet(smiles: str) -> ADMETResult:
    """Calcula descriptores ADMET offline (RDKit) a partir de un SMILES.

    Si el SMILES no es válido, devuelve un ADMETResult con valid=False
    y los campos numéricos en cero.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ADMETResult(valid=False, error="SMILES inválido", mol_formula="")

    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    tpsa = rdMolDescriptors.CalcTPSA(mol)
    hbd = rdMolDescriptors.CalcNumHBD(mol)
    hba = rdMolDescriptors.CalcNumHBA(mol)
    rotb = rdMolDescriptors.CalcNumRotatableBonds(mol)
    aromatic_rings = rdMolDescriptors.CalcNumAromaticRings(mol)
    heavy_atoms = mol.GetNumHeavyAtoms()
    fraction_csp3 = rdMolDescriptors.CalcFractionCSP3(mol)
    molar_refractivity = Crippen.MolMR(mol)
    mol_formula = rdMolDescriptors.CalcMolFormula(mol)

    # ── Regla de Lipinski (Rule of Five) ────────────────────────────
    violations = 0
    if mw > 500:
        violations += 1
    if logp > 5:
        violations += 1
    if hbd > 5:
        violations += 1
    if hba > 10:
        violations += 1
    lipinski_pass = violations <= 1

    # ── Regla de Veber ───────────────────────────────────────────────
    veber_pass = (rotb <= 10) and (tpsa <= 140.0)

    # ── Regla de Egan (BOILED-Egg simplificado, aproximación) ───────
    egan_pass = (tpsa <= 131.6) and (logp <= 5.88)

    # ── Notas interpretativas (heurísticas, no ML) ──────────────────
    if veber_pass and egan_pass:
        absorption_note = (
            "Buena absorción oral probable según criterios de Veber/Egan "
            "(rotación y polaridad superficial dentro de rangos favorables)."
        )
    else:
        absorption_note = (
            "Absorción oral potencialmente limitada: la molécula excede "
            "uno o más límites heurísticos de TPSA, rotación de enlaces o LogP."
        )

    if 1.0 <= logp <= 3.0 and tpsa < 90.0 and mw < 450.0:
        bbb_note = (
            "Permeabilidad a la barrera hematoencefálica probable "
            "(LogP 1-3, TPSA<90 Å², PM<450 g/mol) — estimación aproximada."
        )
    else:
        bbb_note = (
            "Permeabilidad a la barrera hematoencefálica improbable según "
            "los cortes heurísticos usados (LogP, TPSA, PM) — estimación aproximada."
        )

    if mw > 400.0 and tpsa > 90.0:
        pgp_substrate_risk = (
            "Riesgo elevado (heurístico) de ser sustrato de P-glicoproteína "
            "por su tamaño y polaridad superficial — estimación aproximada, no validada."
        )
    else:
        pgp_substrate_risk = (
            "Riesgo bajo (heurístico) de ser sustrato de P-glicoproteína "
            "según PM y TPSA — estimación aproximada, no validada."
        )

    return ADMETResult(
        valid=True,
        error="",
        mol_formula=mol_formula,
        mw=float(mw),
        logp=float(logp),
        tpsa=float(tpsa),
        hbd=int(hbd),
        hba=int(hba),
        rotatable_bonds=int(rotb),
        aromatic_rings=int(aromatic_rings),
        heavy_atoms=int(heavy_atoms),
        fraction_csp3=float(fraction_csp3),
        molar_refractivity=float(molar_refractivity),
        lipinski_violations=int(violations),
        lipinski_pass=lipinski_pass,
        veber_pass=veber_pass,
        egan_pass=egan_pass,
        absorption_note=absorption_note,
        bbb_note=bbb_note,
        pgp_substrate_risk=pgp_substrate_risk,
    )
