"""Conjunto de datos local (offline) de vías clásicas de mecanismo de acción
farmacológico, con fines didácticos.

El contenido busca un nivel de precisión equivalente a textos de referencia
de farmacología (Goodman & Gilman, Katzung). No se realiza ninguna consulta
a internet ni generación por IA: todo el contenido está fijado en este
archivo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PathwayStep:
    label: str          # texto del nodo, ej. "Receptor β-adrenérgico"
    description: str    # explicación breve de ese paso


@dataclass
class Pathway:
    name: str                       # nombre corto, ej. "Adrenérgico β (Gs)"
    category: str                   # ej. "GPCR", "Canal iónico", "Receptor nuclear", "Tirosina cinasa"
    steps: list[PathwayStep]        # secuencia lineal de pasos
    drugs_example: list[str]        # fármacos de ejemplo que actúan por esta vía
    overall_description: str        # párrafo descriptivo completo


PATHWAYS: dict[str, Pathway] = {

    "GPCR-Gs (β-adrenérgico)": Pathway(
        name="GPCR-Gs (β-adrenérgico)",
        category="GPCR",
        steps=[
            PathwayStep("Agonista β-adrenérgico", "Se une al receptor β-adrenérgico (β1, β2 o β3) acoplado a proteína Gs en la membrana plasmática."),
            PathwayStep("Receptor β-adrenérgico (GPCR)", "El receptor activado cambia su conformación y activa a la proteína G heterotrimérica Gs asociada."),
            PathwayStep("Proteína Gs (subunidad Gαs)", "El GDP se intercambia por GTP en Gαs, que se disocia de Gβγ y activa a la adenilato ciclasa."),
            PathwayStep("Adenilato ciclasa", "Enzima de membrana que cataliza la conversión de ATP en AMP cíclico (AMPc)."),
            PathwayStep("AMPc (segundo mensajero)", "El aumento de AMPc intracelular activa a la proteína cinasa A (PKA)."),
            PathwayStep("Proteína cinasa A (PKA)", "Fosforila proteínas blanco específicas del tejido (canales de Ca2+, fosfolambano, enzimas metabólicas)."),
            PathwayStep("Respuesta fisiológica", "Taquicardia e inotropismo positivo (β1 cardíaco), broncodilatación y vasodilatación (β2 en músculo liso), lipólisis (β3)."),
        ],
        drugs_example=["Salbutamol", "Isoproterenol", "Dobutamina", "Adrenalina", "Salmeterol"],
        overall_description=(
            "Los agonistas β-adrenérgicos activan receptores acoplados a la proteína Gs, "
            "que estimula la adenilato ciclasa y eleva el AMPc intracelular, activando a la "
            "PKA. Esta vía media la broncodilatación (β2, útil en asma con salbutamol) y el "
            "aumento de la frecuencia y contractilidad cardíacas (β1, útil en shock cardiogénico "
            "con dobutamina)."
        ),
    ),

    "GPCR-Gi (α2-adrenérgico / opioide)": Pathway(
        name="GPCR-Gi (α2-adrenérgico / opioide)",
        category="GPCR",
        steps=[
            PathwayStep("Agonista (α2-adrenérgico u opioide)", "Se une a un receptor acoplado a proteína Gi, como el receptor α2-adrenérgico o los receptores opioides μ/δ/κ."),
            PathwayStep("Receptor acoplado a Gi (GPCR)", "El receptor activado promueve el intercambio de GDP por GTP en la subunidad Gαi."),
            PathwayStep("Proteína Gi (subunidad Gαi)", "Gαi inhibe directamente a la adenilato ciclasa; Gβγ puede además abrir canales de K+ e inhibir canales de Ca2+ tipo N."),
            PathwayStep("Inhibición de la adenilato ciclasa", "Disminuye la síntesis de AMPc a partir de ATP."),
            PathwayStep("↓ AMPc intracelular", "La menor concentración de AMPc reduce la actividad de la PKA."),
            PathwayStep("↓ Actividad de PKA / hiperpolarización", "Menor fosforilación de blancos dependientes de PKA; la apertura de canales de K+ y el cierre de canales de Ca2+ hiperpolarizan la neurona."),
            PathwayStep("Respuesta fisiológica", "Disminución de la liberación de neurotransmisores (analgesia opioide), reducción del tono simpático (hipotensión con clonidina)."),
        ],
        drugs_example=["Clonidina", "Morfina", "Fentanilo", "Dexmedetomidina", "Metildopa (activa)"],
        overall_description=(
            "Los agonistas de receptores acoplados a Gi (α2-adrenérgicos, opioides) inhiben la "
            "adenilato ciclasa, reduciendo el AMPc, y además modulan directamente canales "
            "iónicos vía Gβγ, lo que produce hiperpolarización neuronal y disminución de la "
            "liberación de neurotransmisores. Es la base de la analgesia opioide y del efecto "
            "antihipertensivo central de la clonidina."
        ),
    ),

    "GPCR-Gq (α1-adrenérgico / muscarínico M1-M3)": Pathway(
        name="GPCR-Gq (α1-adrenérgico / muscarínico M1-M3)",
        category="GPCR",
        steps=[
            PathwayStep("Agonista (α1-adrenérgico o muscarínico M1/M3)", "Se une a un receptor acoplado a proteína Gq, como el receptor α1-adrenérgico o los receptores muscarínicos M1/M3."),
            PathwayStep("Receptor acoplado a Gq (GPCR)", "El receptor activa a la subunidad Gαq mediante intercambio de GDP por GTP."),
            PathwayStep("Proteína Gq (subunidad Gαq)", "Gαq activa a la fosfolipasa C-β (PLCβ) en la membrana plasmática."),
            PathwayStep("Fosfolipasa C-β (PLC)", "Hidroliza el fosfatidilinositol-4,5-bifosfato (PIP2) en dos segundos mensajeros: IP3 y DAG."),
            PathwayStep("IP3 y DAG", "El IP3 difunde al retículo endoplásmico y libera Ca2+ a través de receptores IP3; el DAG permanece en la membrana y activa a la proteína cinasa C (PKC)."),
            PathwayStep("↑ Ca2+ intracelular / activación de PKC", "El Ca2+ se une a calmodulina activando cinasas dependientes de Ca2+/calmodulina; la PKC fosforila otros blancos."),
            PathwayStep("Respuesta fisiológica", "Contracción del músculo liso vascular (vasoconstricción con α1), secreción glandular y contracción del músculo liso gastrointestinal/vesical (M3)."),
        ],
        drugs_example=["Fenilefrina", "Metoxamina", "Pilocarpina", "Betanecol", "Oximetazolina"],
        overall_description=(
            "Los agonistas de receptores Gq (α1-adrenérgicos, muscarínicos M1/M3) activan la "
            "fosfolipasa C, generando IP3 (que libera Ca2+ del retículo endoplásmico) y DAG "
            "(que activa PKC). El aumento de Ca2+ intracelular media la contracción del músculo "
            "liso vascular (vasoconstricción con fenilefrina) y la secreción glandular/contracción "
            "visceral con agonistas muscarínicos como la pilocarpina."
        ),
    ),

    "Canal iónico ligando-dependiente (ionotrópico)": Pathway(
        name="Canal iónico ligando-dependiente (ionotrópico)",
        category="Canal iónico",
        steps=[
            PathwayStep("Agonista (nicotínico o GABAérgico)", "Se une directamente a un receptor-canal ionotrópico, como el receptor nicotínico de acetilcolina o el receptor GABA-A."),
            PathwayStep("Receptor-canal (proteína pentamérica transmembrana)", "La unión del ligando induce un cambio conformacional que abre el poro central del canal."),
            PathwayStep("Apertura del canal iónico", "El canal permite el flujo selectivo de iones específicos (Na+/K+ en el nicotínico; Cl− en el GABA-A)."),
            PathwayStep("Flujo iónico transmembrana", "Entrada de cationes (despolarización) o de Cl− (hiperpolarización), según el canal."),
            PathwayStep("Cambio del potencial de membrana", "Despolarización (excitación, p. ej. en placa neuromuscular) o hiperpolarización (inhibición, p. ej. en neuronas GABAérgicas)."),
            PathwayStep("Respuesta fisiológica", "Contracción muscular y posterior bloqueo despolarizante (succinilcolina) o sedación/efecto ansiolítico-anticonvulsivante (benzodiacepinas)."),
        ],
        drugs_example=["Nicotina", "Succinilcolina", "Diazepam", "Midazolam", "Propofol (sobre GABA-A)"],
        overall_description=(
            "Los receptores ionotrópicos son canales iónicos que se abren directamente al unirse "
            "el ligando, sin segundos mensajeros intermedios, por lo que la respuesta es muy "
            "rápida (milisegundos). El receptor nicotínico permite el flujo de cationes y "
            "despolariza la célula (transmisión neuromuscular); el receptor GABA-A permite la "
            "entrada de Cl− e hiperpolariza la neurona, efecto potenciado alostéricamente por "
            "benzodiacepinas como el diazepam."
        ),
    ),

    "Receptor nuclear / esteroideo": Pathway(
        name="Receptor nuclear / esteroideo",
        category="Receptor nuclear",
        steps=[
            PathwayStep("Hormona lipofílica (esteroide)", "Por su naturaleza lipofílica (p. ej. glucocorticoides, hormonas sexuales), difunde libremente a través de la membrana plasmática."),
            PathwayStep("Difusión transmembrana", "El fármaco/hormona atraviesa la bicapa lipídica sin necesidad de transportadores ni receptores de superficie."),
            PathwayStep("Receptor citoplasmático/nuclear", "Se une a su receptor específico, habitualmente unido a proteínas chaperonas (p. ej. Hsp90) en el citoplasma."),
            PathwayStep("Disociación de chaperonas y dimerización", "La unión del ligando libera al receptor de las proteínas chaperonas y permite su dimerización (homo- o heterodímero)."),
            PathwayStep("Translocación nuclear", "El complejo receptor-ligando dimerizado se transloca al núcleo celular."),
            PathwayStep("Unión al ADN (elemento de respuesta hormonal)", "El dímero se une a secuencias específicas de ADN (p. ej. GRE para glucocorticoides) actuando como factor de transcripción."),
            PathwayStep("Transcripción génica / respuesta", "Modula la transcripción de genes blanco (inducción o represión), con efectos que tardan horas en manifestarse (síntesis de nuevas proteínas)."),
        ],
        drugs_example=["Dexametasona", "Prednisona", "Hidrocortisona", "Estradiol", "Testosterona", "Espironolactona (antagonista mineralocorticoide)"],
        overall_description=(
            "Las hormonas esteroideas y sus análogos farmacológicos atraviesan la membrana "
            "plasmática por difusión y se unen a receptores intracelulares que actúan como "
            "factores de transcripción dependientes de ligando. A diferencia de los GPCR, el "
            "efecto es lento (horas a días) porque requiere síntesis de nuevas proteínas, lo cual "
            "explica el retraso en el efecto antiinflamatorio de los glucocorticoides como la "
            "dexametasona."
        ),
    ),

    "RTK-RAS-RAF-MEK-ERK (EGFR)": Pathway(
        name="RTK-RAS-RAF-MEK-ERK (EGFR)",
        category="Tirosina cinasa",
        steps=[
            PathwayStep("Ligando de crecimiento (EGF)", "El factor de crecimiento epidérmico (EGF) u otro ligando se une al dominio extracelular del receptor EGFR."),
            PathwayStep("Dimerización del receptor (EGFR)", "La unión del ligando induce la dimerización (homo- o heterodimerización) de dos receptores tirosina cinasa."),
            PathwayStep("Autofosforilación de tirosinas", "Los dominios cinasa intracelulares se transfosforilan mutuamente en residuos de tirosina del dominio C-terminal."),
            PathwayStep("Reclutamiento de proteínas adaptadoras (GRB2/SOS)", "Las fosfotirosinas reclutan proteínas con dominios SH2 (GRB2), que a su vez reclutan al factor intercambiador SOS."),
            PathwayStep("Activación de RAS", "SOS cataliza el intercambio de GDP por GTP en RAS, activándolo."),
            PathwayStep("Cascada RAF → MEK → ERK", "RAS activa a RAF (MAPKKK), que fosforila y activa a MEK (MAPKK), que a su vez fosforila y activa a ERK (MAPK)."),
            PathwayStep("ERK nuclear / transcripción", "ERK se transloca al núcleo y fosforila factores de transcripción que promueven la proliferación y supervivencia celular."),
        ],
        drugs_example=["Erlotinib", "Gefitinib", "Cetuximab (anticuerpo anti-EGFR)", "Trametinib (inhibidor de MEK)", "Vemurafenib (inhibidor de BRAF mutado)"],
        overall_description=(
            "Los receptores tirosina cinasa (RTK) como el EGFR transducen señales de factores de "
            "crecimiento mediante dimerización, autofosforilación y activación secuencial de la "
            "cascada RAS-RAF-MEK-ERK, que finalmente promueve la proliferación celular. En "
            "oncología, esta vía se bloquea con inhibidores de tirosina cinasa (erlotinib, "
            "gefitinib) o anticuerpos monoclonales (cetuximab) cuando está hiperactivada en "
            "tumores."
        ),
    ),

    "Receptor de insulina – PI3K/Akt": Pathway(
        name="Receptor de insulina – PI3K/Akt",
        category="Tirosina cinasa",
        steps=[
            PathwayStep("Insulina", "Se une a la subunidad α extracelular del receptor de insulina (un receptor tirosina cinasa tetramérico preformado)."),
            PathwayStep("Receptor de insulina (RTK)", "La unión de insulina induce un cambio conformacional que activa el dominio cinasa intracelular de la subunidad β."),
            PathwayStep("Autofosforilación y fosforilación de IRS-1", "El receptor se autofosforila y a su vez fosforila al sustrato del receptor de insulina 1 (IRS-1)."),
            PathwayStep("Activación de PI3K", "IRS-1 fosforilado recluta y activa a la fosfatidilinositol-3-cinasa (PI3K)."),
            PathwayStep("Generación de PIP3 y activación de Akt", "PI3K convierte PIP2 en PIP3, que recluta y permite la activación de la proteína cinasa Akt (PKB)."),
            PathwayStep("Translocación de GLUT4", "Akt activada promueve la translocación de los transportadores de glucosa GLUT4 desde vesículas intracelulares hacia la membrana plasmática."),
            PathwayStep("Captación de glucosa / respuesta metabólica", "Aumenta la captación de glucosa en músculo y tejido adiposo; Akt también inhibe la gluconeogénesis hepática y promueve la síntesis de glucógeno y proteínas."),
        ],
        drugs_example=["Insulina regular", "Insulina glargina", "Insulina lispro", "Insulina detemir"],
        overall_description=(
            "El receptor de insulina es un receptor tirosina cinasa que, tras la unión de la "
            "hormona, fosforila al IRS-1 y activa la vía PI3K/Akt, culminando en la "
            "translocación de GLUT4 a la membrana plasmática y el aumento de la captación de "
            "glucosa. Esta vía es la base farmacológica del tratamiento sustitutivo con insulina "
            "en diabetes mellitus."
        ),
    ),

    "JAK-STAT (receptores de citocinas)": Pathway(
        name="JAK-STAT (receptores de citocinas)",
        category="Tirosina cinasa",
        steps=[
            PathwayStep("Citocina (p. ej. interleucina, interferón)", "Se une a su receptor transmembrana específico, que carece de actividad cinasa intrínseca."),
            PathwayStep("Receptor de citocina", "La unión del ligando induce la dimerización u oligomerización del receptor, acercando las cinasas JAK asociadas."),
            PathwayStep("Activación de JAK (Janus cinasa)", "Las JAK asociadas al receptor (JAK1, JAK2, JAK3, TYK2) se transfosforilan y activan mutuamente."),
            PathwayStep("Fosforilación de residuos del receptor", "Las JAK activadas fosforilan residuos de tirosina en la cola citoplasmática del receptor, creando sitios de acoplamiento."),
            PathwayStep("Reclutamiento y fosforilación de STAT", "Las proteínas STAT se acoplan a estos sitios mediante dominios SH2 y son fosforiladas por JAK."),
            PathwayStep("Dimerización y translocación nuclear de STAT", "Los STAT fosforilados forman dímeros y se translocan al núcleo."),
            PathwayStep("Transcripción génica", "Los dímeros de STAT actúan como factores de transcripción, regulando genes de respuesta inmune e inflamatoria."),
        ],
        drugs_example=["Tofacitinib (inhibidor de JAK1/JAK3)", "Baricitinib (inhibidor de JAK1/JAK2)", "Ruxolitinib (inhibidor de JAK1/JAK2)"],
        overall_description=(
            "La vía JAK-STAT transduce señales de numerosas citocinas e interferones: el "
            "receptor recluta y activa cinasas JAK, que fosforilan al propio receptor y a "
            "proteínas STAT, las cuales dimerizan y se translocan al núcleo para regular la "
            "transcripción génica inmune. Los inhibidores de JAK (tofacitinib, baricitinib) se "
            "usan como inmunosupresores en artritis reumatoide y otras enfermedades autoinmunes."
        ),
    ),

    "NO–GMPc (vasodilatación)": Pathway(
        name="NO–GMPc (vasodilatación)",
        category="Enzima/segundo mensajero",
        steps=[
            PathwayStep("Óxido nítrico (NO) / nitrovasodilatadores", "El NO endógeno (producido por la NO sintasa endotelial) o liberado por fármacos como la nitroglicerina difunde hacia el músculo liso vascular."),
            PathwayStep("Difusión hacia la célula de músculo liso", "Por su naturaleza gaseosa y lipofílica, el NO atraviesa libremente las membranas celulares."),
            PathwayStep("Activación de la guanilato ciclasa soluble (GCs)", "El NO se une al grupo hemo de la guanilato ciclasa soluble citoplasmática, activándola."),
            PathwayStep("Producción de GMPc", "La GCs activada cataliza la conversión de GTP en GMP cíclico (GMPc)."),
            PathwayStep("Activación de la proteína cinasa G (PKG)", "El aumento de GMPc activa a la PKG, que fosforila diversos blancos relacionados con la contracción muscular."),
            PathwayStep("Relajación del músculo liso vascular", "La PKG reduce el Ca2+ intracelular y desensibiliza la maquinaria contráctil, produciendo relajación y vasodilatación."),
        ],
        drugs_example=["Nitroglicerina", "Dinitrato de isosorbida", "Nitroprusiato de sodio", "Sildenafil (inhibidor de PDE5, prolonga el GMPc)", "Tadalafilo"],
        overall_description=(
            "El óxido nítrico activa la guanilato ciclasa soluble, generando GMPc que activa a la "
            "PKG y produce relajación del músculo liso vascular. Los nitratos orgánicos "
            "(nitroglicerina) liberan NO directamente, mientras que fármacos como el sildenafil "
            "actúan inhibiendo la fosfodiesterasa-5 (PDE5), la enzima que degrada el GMPc, "
            "prolongando así su efecto vasodilatador (uso en disfunción eréctil e hipertensión "
            "pulmonar)."
        ),
    ),

    "Inhibición enzimática directa (COX/AINEs)": Pathway(
        name="Inhibición enzimática directa (COX/AINEs)",
        category="Inhibición enzimática",
        steps=[
            PathwayStep("Fármaco inhibidor (AINE)", "El antiinflamatorio no esteroideo (AINE) se une al sitio activo (o a un sitio adyacente) de la enzima ciclooxigenasa (COX-1 y/o COX-2)."),
            PathwayStep("Unión al sitio activo de la ciclooxigenasa", "El fármaco bloquea de forma competitiva o irreversible (ácido acetilsalicílico) el canal hidrofóbico por donde el ácido araquidónico accede al sitio catalítico."),
            PathwayStep("Bloqueo de la conversión de ácido araquidónico", "Se impide la conversión enzimática del ácido araquidónico en prostaglandina G2/H2 (PGG2/PGH2), el paso limitante de la síntesis de prostanoides."),
            PathwayStep("↓ Síntesis de prostaglandinas y tromboxanos", "Disminuye la producción de prostaglandinas (PGE2, PGI2) y tromboxano A2, mediadores de inflamación, dolor, fiebre y agregación plaquetaria."),
            PathwayStep("Respuesta farmacológica", "Efecto analgésico, antipirético y antiinflamatorio (inhibición de COX-2 principalmente); inhibición de la agregación plaquetaria (inhibición de COX-1/tromboxano A2, ácido acetilsalicílico a dosis bajas)."),
        ],
        drugs_example=["Ibuprofeno", "Ácido acetilsalicílico (aspirina)", "Naproxeno", "Diclofenaco", "Celecoxib (selectivo COX-2)"],
        overall_description=(
            "Los AINEs inhiben directamente la enzima ciclooxigenasa (COX-1 y/o COX-2), "
            "bloqueando la conversión del ácido araquidónico en prostaglandinas y tromboxanos. "
            "Esto reduce la inflamación, el dolor y la fiebre, y en el caso del ácido "
            "acetilsalicílico a dosis bajas (inhibición irreversible de COX-1 plaquetaria) "
            "produce un efecto antiagregante plaquetario duradero, base de su uso en "
            "prevención cardiovascular."
        ),
    ),

}


def get_pathway_names() -> list[str]:
    """Devuelve la lista de nombres de vías disponibles, en el orden definido."""
    return list(PATHWAYS.keys())


def get_pathway(name: str) -> Pathway:
    """Devuelve el objeto Pathway correspondiente al nombre dado.

    Lanza KeyError si el nombre no existe (se espera que la UI solo pase
    nombres obtenidos de get_pathway_names()).
    """
    return PATHWAYS[name]


def search_pathways_by_drug(drug_name: str) -> list[Pathway]:
    """Búsqueda simple, insensible a mayúsculas, por coincidencia de
    subcadena en drugs_example."""
    query = (drug_name or "").strip().lower()
    if not query:
        return []
    results = []
    for pathway in PATHWAYS.values():
        for drug in pathway.drugs_example:
            if query in drug.lower():
                results.append(pathway)
                break
    return results
