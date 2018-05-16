/* 
   Holds information on where a proc is being redirected to. 
   Could be a job name or a group name.
*/

ALTER TABLE proc ADD str_redirect VARCHAR2(255);
