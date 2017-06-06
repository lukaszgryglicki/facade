# https://hub.docker.com/r/lukaszgryglicki/facade/
FROM debian
MAINTAINER Łukasz Gryglicki<lukaszgryglicki@o2.pl>
WORKDIR /facade
ADD . /facade
RUN ./utilities/mysql_root_pwd.sh
RUN apt-get update
RUN apt-get install -y `cat requirements.txt`
RUN service mysql start && mysql -uroot -proot < utilities/mysql_init.sql
RUN ln -s /etc/apache2/mods-available/rewrite.load /etc/apache2/mods-enabled/rewrite.load
RUN sed -i 's/AllowOverride None/AllowOverride All/' /etc/apache2/apache2.conf
RUN rm -rf /var/www/html
RUN cp -R /facade/ /var/www/html
RUN service apache2 start
RUN cp php/info.php /var/www/html/info.php
EXPOSE 80
CMD /facade/server.sh
