# https://hub.docker.com/r/lukaszgryglicki/facade/
FROM debian
MAINTAINER Łukasz Gryglicki<lukaszgryglicki@o2.pl>
WORKDIR /facade
ADD . /facade
RUN ./utilities/mysql_root_pwd.sh
RUN apt-get update
RUN apt-get install -y `cat requirements.txt`
RUN service mysql start && mysql -uroot -proot < utilities/mysql_init.sql
RUN service apache2 start
EXPOSE 80
CMD /facade/server.sh
