delete from journey where privatecode not like 'GVB:%' AND
availabilityconditionref not in (select 
id from activeavailabilitycondition WHERE 
todate >= date 'yesterday');

DELETE FROM availabilityconditionday WHERE availabilityconditionref not in (
select distinct availabilityconditionref from journey
);

DELETE FROM availabilitycondition WHERE ID not in (
select distinct availabilityconditionref from journey
);

DELETE FROM pointinjourneypattern WHERE journeypatternref NOT in (
SELECT distinct journeypatternref from journey
);

DELETE FROM pointintimedemandgroup WHERE timedemandgroupref NOT in (
SELECT distinct timedemandgroupref from journey
);

DELETE FROM administrativezone WHERE id NOT IN (
SELECT DISTINCT administrativezoneref FROM pointinjourneypattern
);

DELETE FROM journeypattern WHERE id not in (
SELECT distinct journeypatternref from pointinjourneypattern
);

DELETE FROM timedemandgroup WHERE id not in (
SELECT distinct timedemandgroupref from pointintimedemandgroup
);

--DELETE FROM destinationdisplay WHERE id not in (
--select distinct destinationdisplayref FROM journeypattern
--UNION
--select distinct destinationdisplayref FROM pointinjourneypattern WHERE
--destinationdisplayref is not null
--);

DELETE FROM pointinroute WHERE routeref not in (
SELECT DISTINCT routeref FROM journeypattern
);

DELETE FROM route WHERE id not in (
SELECT DISTINCT routeref FROM journeypattern
);

DELETE FROM line where id not in (
SELECT DISTINCT lineref FROM route
);

DELETE FROM STOPPOINT where operator_id not like 'IFF%' AND id not in (
SELECT DISTINCT id from (
SELECT DISTINCT pointref as id FROM pointinjourneypattern
UNION
SELECT DISTINCT onwardpointref as id FROM pointinjourneypattern
WHERE onwardpointref is not null) as x
);

DELETE from stoparea where id not in (select distinct stoparearef from stoppoint where stoparearef is not null) AND operator_id not like 'IFF%';

DELETE FROM stoppoint as sp
WHERE sp.operator_id in (select
sp.operator_id
from stoppoint as sp
WHERE sp.operator_id like 'IFF:%'
group by sp.operator_id having count(*) > 1) AND id not in (
select DISTINCT ON (sp.operator_id)
sp.id
from stoppoint as sp
WHERE sp.operator_id like 'IFF:%'
ORDER BY operator_id ASC, sp.ID DESC);
