from kv1_811 import *
from inserter import insert,version_imported
import urllib2
from lxml import etree
import logging

logger = logging.getLogger("importer")

url_gvb = 'http://195.193.209.12/gvbpublicatieinternet/KV1/'
kv1index_gvb = url_gvb+'KV1index.xml'

def getDataSource():
    return { '1' : {
                          'operator_id' : 'GVB',
                          'name'        : 'GVB',
                          'description' : 'GVB KV1delta leveringen',
                          'email'       : 'info@gvb.nl',
                          'url'         : kv1index_gvb}}

def getOperator():
    return { 'GVB' : {'privatecode' : 'GVB',
                               'operator_id' : 'GVB',
                               'name'        : 'GVB',
                               'phone'       : '0900-8011',
                               'url'         : 'http://www.gvb.nl',
                               'timezone'    : 'Europe/Amsterdam',
                               'language'    : 'nl'}}

def getMergeStrategies(conn):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
SELECT 'UNITCODE' as type,dataownercode||':'||organizationalunitcode as unitcode,min(validfrom) as fromdate,max(validthru) as todate FROM schedvers GROUP BY dataownercode,organizationalunitcode
""")
    rows = cur.fetchall()
    cur.close()
    return rows

def calculateTimeDemandGroupsGVB(conn):
    cur = conn.cursor('timdemgrps',cursor_factory=psycopg2.extras.RealDictCursor)
    timdemgroup_ids = {}
    timdemgroups = {}
    journeyinfo = {}
    cur.execute("""
SELECT concat_ws(':',version, dataownercode, organizationalunitcode, schedulecode, scheduletypecode, lineplanningnumber, journeynumber) as 
JOURNEY_id, 
array_agg(cast(patternpass.stoporder as integer) order by patternpass.stoporder) as 
stoporders,array_agg(toseconds(coalesce(targetarrivaltime,targetdeparturetime),0) order by patternpass.stoporder) as 
arrivaltimes,array_agg(toseconds(coalesce(targetdeparturetime,targetarrivaltime),0) order by patternpass.stoporder) as departuretimes
FROM patternpass JOIN pujopass USING (version,dataownercode,lineplanningnumber,journeypatterncode,userstopcode)
GROUP BY JOURNEY_id
""")
    for row in cur:
        points = [(row['stoporders'][0],0,0)]
        dep_time = row['departuretimes'][0]
        for i in range(len(row['stoporders'][:-1])):     
            cur_arr_time = row['arrivaltimes'][i+1]
            cur_dep_time = row['departuretimes'][i+1]
            points.append((row['stoporders'][i+1],cur_arr_time-dep_time,cur_dep_time-cur_arr_time))
        m = md5.new()
        m.update(str(points))
        timdemgrp = {'POINTS' : []}
        for point in points:
            point_dict = {'pointorder' : point[0],'totaldrivetime' : point[1], 'stopwaittime' : point[2]}
            timdemgrp['POINTS'].append(point_dict)
        journeyinfo[row['journey_id']] = {'departuretime' : dep_time, 'timedemandgroupref' : m.hexdigest()}
        timdemgrp['operator_id'] = m.hexdigest()
        timdemgroups[m.hexdigest()] = timdemgrp
    cur.close()
    return (journeyinfo,timdemgroups)

def import_zip(path,filename,meta=None):
    deprecated,conn = load(path,filename)
    try:
        data = {}
        data['DATASOURCE'] = getDataSource()
        data['OPERATOR'] = getOperator()
        data['MERGESTRATEGY'] = getMergeStrategies(conn)
        data['VERSION'] = {}
        data['VERSION']['1'] = {'privatecode'   : ':'.join(['GVB',meta['key'],meta['dataownerversion']]),
                                'datasourceref' : '1',
                                'operator_id'   : ':'.join(['GVB',meta['key'],meta['dataownerversion']]),
                                'startdate'     : meta['validfrom'],
                                'enddate'       : meta['validthru'],
                                'description'   : filename}
        data['DESTINATIONDISPLAY'] = getDestinationDisplays(conn)
        data['LINE'] = getLines(conn)
        data['STOPPOINT'] = getStopPoints(conn)
        data['STOPAREA'] = getStopAreas(conn)
        data['AVAILABILITYCONDITION'] = getAvailabilityConditionsFromSchedvers(conn)
        data['PRODUCTCATEGORY'] = getBISONproductcategories()
        data['ADMINISTRATIVEZONE'] = getAdministrativeZones(conn)
        timedemandGroupRefForJourney,data['TIMEDEMANDGROUP'] = calculateTimeDemandGroupsGVB(conn)
        routeRefForPattern,data['ROUTE'] = clusterPatternsIntoRoute(conn,getPool811)
        data['JOURNEYPATTERN'] = getJourneyPatterns(routeRefForPattern,conn,data['ROUTE'])
        data['JOURNEY'] = getJourneys(timedemandGroupRefForJourney,conn)
        data['NOTICEASSIGNMENT'] = {}
        data['NOTICE'] = {}
        data['NOTICEGROUP'] = {}
        conn.close()
        insert(data)
    except:
        raise

def download(url,filename,version):
    u = urllib2.urlopen(url)
    f = open('/tmp/'+filename, 'wb')

    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (filename, file_size)

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break
        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print status,
    print
    f.close()
    import_zip('/tmp',filename,version)

def multikeysort(items, columns):
    from operator import itemgetter
    comparers = [ ((itemgetter(col[1:].strip()), -1) if col.startswith('-') else (itemgetter(col.strip()), 1)) for col in columns]  
    def comparer(left, right):
        for fn, mult in comparers:
            result = cmp(fn(left), fn(right))
            if result:
                return mult * result
        else:
            return 0
    return sorted(items, cmp=comparer)

def sync():
    tree = etree.parse(kv1index_gvb)
    index = []
    for periode in tree.findall('periode'):
        file = {}
        file['key'] = periode.attrib['key']
        file['filename'] = periode.find('zipfile').text
        file['dataownerversion'] = periode.find('versie').text
        file['ispublished'] = periode.find('isgepubliceerd').text
        file['publishdate'] = periode.find('publicatiedatum').text
        file['isbaseline'] = (periode.find('isbaseline').text == 'true')
        if file['ispublished'] == 'false':
            deletedelta(conn,file['key'])
        file['validfrom'] = periode.find('startdatum').text
        file['validthru'] = periode.find('einddatum').text
        if file['key'] == 'a00bac99-e404-4783-b2f7-a39d48747999':
            file['isbaseline'] = True
        index.append(file)
    index = multikeysort(index, ['-isbaseline','publishdate'])
    for f in index:
        if not version_imported(':'.join(['GVB',f['key'],f['dataownerversion']])):
            logger.info('Import file %s version %s' % (f['filename'],str(f['dataownerversion'])))
            download(url_gvb+f['filename'],f['filename'],f)
