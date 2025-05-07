FROM debian:bullseye

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    asterisk \
    asterisk-modules \
    curl \
    net-tools \
    vim \
    iputils-ping \
    && apt-get clean

# Копируем конфиги
COPY asterisk/ /etc/asterisk/

# Открываем порты (SIP, RTP, AMI, ARI)
EXPOSE 5060/udp 5060/tcp 5038 8088

CMD ["asterisk", "-f"]

# root@fdaa6c08265d:/# ls /etc/asterisk/
# acl.conf                cdr_custom.conf          cli.conf                festival.conf     musiconhold.conf         res_curl.conf          ss7.timers
# adsi.conf               cdr_manager.conf         cli_aliases.conf        followme.conf     muted.conf               res_fax.conf           stasis.conf
# agents.conf             cdr_mysql.conf           cli_permissions.conf    func_odbc.conf    ooh323.conf              res_ldap.conf          statsd.conf
# alarmreceiver.conf      cdr_odbc.conf            codecs.conf             geolocation.conf  osp.conf                 res_odbc.conf          stir_shaken.conf
# alsa.conf               cdr_pgsql.conf           confbridge.conf         hep.conf          oss.conf                 res_parking.conf       telcordia-1.adsi
# amd.conf                cdr_sqlite3_custom.conf  config_test.conf        http.conf         phone.conf               res_pgsql.conf         test_sorcery.conf
# app_mysql.conf          cdr_syslog.conf          console.conf            iax.conf          phoneprov.conf           res_pktccops.conf      udptl.conf
# app_skel.conf           cdr_tds.conf             dbsep.conf              iaxprov.conf      pjproject.conf           res_snmp.conf          users.conf
# ari.conf                cel.conf                 dnsmgr.conf             indications.conf  pjsip.conf               res_stun_monitor.conf  voicemail.conf
# ast_debug_tools.conf    cel_beanstalkd.conf      dsp.conf                logger.conf       pjsip_notify.conf        resolver_unbound.conf  vpb.conf
# asterisk.adsi           cel_custom.conf          enum.conf               manager.conf      pjsip_wizard.conf        rtp.conf               xmpp.conf
# asterisk.conf           cel_odbc.conf            extconfig.conf          manager.d         queuerules.conf          say.conf
# calendar.conf           cel_pgsql.conf           extensions.ael          meetme.conf       queues.conf              sip.conf
# ccss.conf               cel_sqlite3_custom.conf  extensions.conf         minivm.conf       res_config_mysql.conf    sip_notify.conf
# cdr.conf                cel_tds.conf             extensions.lua          misdn.conf        res_config_sqlite.conf   sla.conf
# cdr_adaptive_odbc.conf  chan_dahdi.conf          extensions_minivm.conf  modules.conf      res_config_sqlite3.conf  smdi.conf
# cdr_beanstalkd.conf     chan_mobile.conf         features.conf           motif.conf        res_corosync.conf        sorcery.conf
