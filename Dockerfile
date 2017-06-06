FROM debian
MAINTAINER Łukasz Gryglicki<lukaszgryglicki@o2.pl>
WORKDIR /facade
ADD . /facade
RUN ./utilities/mysql_root_pwd.sh
RUN apt-get update
RUN apt-get install -y `cat requirements.txt`
RUN service mysql start && mysql -uroot -proot < utilities/mysql_init.sql
EXPOSE 80
