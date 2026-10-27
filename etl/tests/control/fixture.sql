INSERT INTO control.source VALUES ('s','public');
INSERT INTO control.dataset VALUES ('d','s','v1','public');
INSERT INTO control.partition VALUES ('p','d');
INSERT INTO control.artifact VALUES ('00000000-0000-0000-0000-000000000001','p','raw/s/d/p/' || repeat('a',64),repeat('a',64),'public');
