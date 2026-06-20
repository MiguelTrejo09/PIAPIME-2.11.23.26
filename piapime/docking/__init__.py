"""Módulo de acoplamiento molecular (AutoDock Vina, offline/local).

Requiere que el usuario tenga instalado el binario de AutoDock Vina en el
PATH del sistema (o indique su ruta manualmente). La preparación del ligando
usa RDKit + meeko (opcionales); el receptor debe proporcionarse ya preparado
en formato .pdbqt. No se realiza ninguna llamada de red.
"""
