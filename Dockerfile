# https://hub.docker.com/r/lukaszgryglicki/facade/
FROM debian
MAINTAINER Łukasz Gryglicki<lukaszgryglicki@o2.pl>
WORKDIR /facade
ADD . /facade
RUN ./utilities/mysql_root_pwd.sh
# RUN wget https://repo.mysql.com/mysql-apt-config_0.8.6-1_all.deb
# RUN apt-key adv --keyserver pgp.mit.edu --recv-keys 5072E1F5
# RUN echo 'deb http://repo.mysql.com/apt/debian jessie mysql-5.7' > /etc/apt/sources.list.d/mysql.list
RUN apt-get update
RUN apt-get install -y `cat requirements.txt`
RUN service mysql start && mysql -uroot -proot < utilities/mysql_init.sql
RUN ln -s /etc/apache2/mods-available/rewrite.load /etc/apache2/mods-enabled/rewrite.load
RUN sed -i 's/AllowOverride None/AllowOverride All/' /etc/apache2/apache2.conf
RUN useradd -p facade facade
RUN echo 'facade:facade' | chpasswd
RUN echo 'root:root' | chpasswd
RUN adduser facade sudo
RUN rm -rf /var/www/html
RUN cp -R /facade/ /var/www/html
# RUN cp php/info.php /var/www/html/info.php
RUN service apache2 start
RUN service ssh start
EXPOSE 80 22
CMD /facade/server.sh
