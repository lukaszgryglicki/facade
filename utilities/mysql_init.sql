create database facade;
create user 'facade'@'localhost' identified by 'facade';
grant all privileges on facade.* to 'facade'@'localhost';
flush privileges;
