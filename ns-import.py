import importers.ns
import logging
import sys

logger = logging.getLogger("importer")
fh = logging.FileHandler('error.log')
fh.setLevel(logging.ERROR)
ch = logging.StreamHandler(stream=sys.stdout)
ch.setLevel(logging.INFO)

logger.addHandler(fh)
logger.addHandler(ch)

path = '.'
filename= sys.argv[1]
meta = {'dataownercode' : 'NS'}

importers.ns.import_zip(path,filename,meta)
