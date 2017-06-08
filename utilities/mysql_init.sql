create database facade character set utf8mb4 collate utf8mb4_unicode_ci;
create user 'facade'@'localhost' identified by 'facade';
grant all privileges on facade.* to 'facade'@'localhost';
flush privileges;
