__version__ = '1.5.5'
__author__  = 'ScottSmudger'
 
import b3, re, threading
import b3.events
import b3.plugin
import b3.cron
import time
import MySQLdb
from MySQLdb import OperationalError
 
class Ar51Plugin(b3.plugin.Plugin):
    requiresConfigFile = True
    _cronTab = None
    server_ip = "127.0.0.1"
    server_name = "[AR51] Test"
    
    # --------------------------------------------------------
    #   Load Config/Set Default Values
    # --------------------------------------------------------
    def onLoadConfig(self):
        # Get config values
        self.verbose('Loading general settings')
        try:
            self.clan_tags = self.config.get('general', 'clan_tags')
        except:
            self.warning("Unable to get value for clan_tags")
            self.clan_tags = "AR51"
        try:
            self.min_level = self.config.getint('general', 'min_level')
        except:
            self.warning("Unable to get value for min_level - setting default: 10")
            self.min_level = 10
        try:
            self.warn_reason = self.config.get('general', 'warn_reason')
        except:
            self.warning("Unable to get value for warn_reason - setting default: You are not allowed to wear our clan tags!")
            self.warn_reason = 'You are not allowed to wear our clan tags!'
        try:
            self.warn_duration = self.config.getDuration('general', 'warn_duration')
        except:
            self.warning("Unable to get value for warn_duration - setting default: 1h")
            self.warn_duration = "1h"
        try:
            self.warn_interval = self.config.getDuration('general', 'warn_interval')
        except:
            self.warning("Unable to get value for warn_interval - setting default: 30")
            self.warn_interval = 30
        try:
            self.rage_quit = self.config.getboolean('general', 'rage_quit')
        except:
            self.warning("Unable to get value for rage_quit - setting default: yes")
            self.rage_quit = True
        try:
            self.rage_interval = self.config.getint('general', 'rage_interval')
        except:
            self.warning("Unable to get value for rage_interval - setting default: 30")
            self.rage_interval = 30
        try:
            self.server_logging = self.config.getboolean('general', 'server_logging')
        except:
            self.warning("Unable to get value for server_logging - setting default: yes")
            self.server_logging = True
        try:
            self.time_online = self.config.getboolean('general', 'time_online')
        except:
            self.warning("Unable to get value for time_online - setting default: yes")
            self.time_online = True
        try:
            self.watch_system = self.config.getboolean('general', 'watch_system')
        except:
            self.warning("Unable to get value for watch_system - setting default: yes")
            self.watch_system = True
        self.verbose('Loading forum settings')
        try:
            self.db_shouts = self.config.getboolean('forum', 'db_shouts')
            self.db_host = self.config.get('forum', 'db_host')
            self.db_port = self.config.getint('forum', 'db_port')
            self.db_user = self.config.get('forum', 'db_user')
            self.db_pass = self.config.get('forum', 'db_pass')
            self.db_db = self.config.get('forum', 'db_db')
        except:
            self.error("Unable to get forum details. Disabled db_shouts")
            self.db_shouts = False
        try:
            self.kick_afks = self.config.getboolean('general', 'kick_afks')
            self.afk_time = self.config.getDuration('general', 'afk_time')
        except:
            self.warning("Setting defaults for AFK kicks: Enabled, 5 mins")
            self.kick_afks = True
            self.afk_time = 60
        self.verbose('Loading IP ban settings')
        try:
            self.ip_bans = self.config.getboolean('ipbans', 'ip_bans')
            self.ip_bans_level = self.config.get('ipbans', 'ip_bans_level')
            self.ip_list = self.config.get("ips/ip")
        except:
            self.warning("Setting defaults for IP bans: Disabled, level 80")
            self.ip_bans = False
            self.ip_bans_level = 80
            self.ip_list = ()
        
        print len(self.ip_list)
    # --------------------------------------------------------
    #   Setup variables and objects
    # --------------------------------------------------------
    def onStartup(self):
        # Set global values
        self._adminPlugin = self.console.getPlugin('admin')
        self.query = self.console.storage.query
        self.clients = self.console.clients
        self.loud = self.console.say
        self.watch_list = {}
        self.time_list = {}
        self.afk_list = {}
        # We're stuffed if we can't get the admin plugin
        if not self._adminPlugin:
            self.error('Could not find admin plugin')
            return
        # # Load cron
        # if self._cronTab:
            # # remove existing crontab
            # self.console.cron - self._cronTab
    
        # self._cronTab = b3.cron.PluginCronTab(self, self.updateForumTopic, hour = 0)
        # self.console.cron + self._cronTab
        # Set these if we are not testing - Test environment crashes
        if __name__ != '__main__':
            self.server_ip = self.console.getCvar("net_ip")["value"] + ":" + self.console.getCvar("net_port")["value"]
            self.server_name = self.console.getCvar("sv_hostname")["value"] + "^7"
        # Register commands
        self.verbose('Registering commands')
        #self._adminPlugin.registerCommand(self, 'test', 0, self.cmd_test)
        self._adminPlugin.registerCommand(self, 'ar51', self.min_level, self.cmd_ar51)
        self._adminPlugin.registerCommand(self, 'noob', 100, self.cmd_boob, "nb")
        self._adminPlugin.registerCommand(self, 'boob', self.min_level, self.cmd_boob, "bb")
        self._adminPlugin.registerCommand(self, 'gg', 100, self.cmd_gg)
        if self.server_logging:
            self.debug("server_logging is enabled")
            self._adminPlugin.registerCommand(self, 'online', self.min_level, self.cmd_online)
        if self.time_online:
            self.debug("time_online is enabled")
            self._adminPlugin.registerCommand(self, 'tonline', self.min_level, self.cmd_tonline)
        # Register our events
        self.verbose('Registering events')
        self.registerEvent(b3.events.EVT_CLIENT_NAME_CHANGE)
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.registerEvent(b3.events.EVT_GAME_EXIT)
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)
        self.registerEvent(b3.events.EVT_GAME_ROUND_END)
        self.registerEvent(b3.events.EVT_CLIENT_TEAM_CHANGE)
        # Register EVT_CLIENT_KILL if rage_quit is enabled
        if self.rage_quit:
            self.debug("rage_quit is enabled")
            self.registerEvent(b3.events.EVT_CLIENT_KILL)
        # Create the mysql connection and register the command
        if self.db_shouts:
            self.debug("db_shouts is enabled")
            self._adminPlugin.registerCommand(self, 'admin', 0, self.cmd_admin, "calladmin")
            self.forum = Forum(self.db_host, self.db_port, self.db_user, self.db_pass, self.db_db)
        # Watch system
        if self.watch_system:
            self.debug("watch_system is enabled")
            self._adminPlugin.registerCommand(self, 'watch', self.min_level, self.cmd_watch)
        # IP bans
        if self.ip_bans:
            self._adminPlugin.registerCommand(self, 'iplist', self.ip_bans_level, self.cmd_iplist)
        self.loud('AR51 Plugin v%s by %s started' % (__version__, __author__))
    
    # --------------------------------------------------------
    #   Deal with Events
    # --------------------------------------------------------
    def onEvent(self, event):
        # Handle the events
        if event.type == b3.events.EVT_CLIENT_NAME_CHANGE:
            self.checkName(event.client)
            
        elif event.type == b3.events.EVT_CLIENT_AUTH:
            # Start to log clients time online
            self.timeOnline(event.type, event.client)
            # Check for tags
            self.checkName(event.client)
            # Update clients current server
            if self.server_logging:
                self.updateClientJoin(event.client)
                
        elif event.type == b3.events.EVT_CLIENT_KILL and self.rage_quit:
            self.rageQuit(event.type, event.target)
            
        elif event.type == b3.events.EVT_CLIENT_DISCONNECT:
            # Finish to log clients time online
            self.timeOnline(event.type, event.client)
            # Remove clients last server
            if self.server_logging:
                self.updateClientQuit(event.client)
            # If rage_quit is enabled
            if self.rage_quit:
                self.rageQuit(event.type, event.client)
                
        elif event.type == b3.events.EVT_GAME_EXIT or event.type == b3.events.EVT_GAME_ROUND_END:
            # Clear lists
            self.debug("Clearing the watch, time and afk lists")
            for client in self.watch_list:
                del client
            for client in self.time_list:
                del client
            for client in self.afk_list:
                del client
                
        elif event.type == b3.events.EVT_GAME_ROUND_START or event.type == b3.events.EVT_CLIENT_TEAM_CHANGE:
            if self.kick_afks:
                if event.client.team == b3.TEAM_SPEC: #and event.client.maxLevel < self.min_level:
                    self.debug("Inserting %s (@%s) into the afk_list" % (event.client.name, event.client.id))
                    self.afk_list[event.client.id] = 0
                    self.checkSpec(event.client)
        else:
            self.dumpEvent(event)
    
    # --------------------------------------------------------
    #   Commands Section
    # --------------------------------------------------------
    # Deals with the !ar51 command
    def cmd_ar51(self, data, client, cmd):
        self.debug('Getting ar51 members/admins')
        self.outputAR51(client, cmd)
    
    # Deals with the !online command
    def cmd_online(self, data, client, cmd):
        if data:
            input = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if sclient:
                last_server = self.getLastServerByDBID(sclient.id)
                if last_server:
                    cmd.sayLoudOrPM(client, "Client %s (@%s) is currently on server %s (%s)" % (sclient.exactName, sclient.id, last_server["server_name"] + "^7", last_server["server_ip"]))
                else:
                    cmd.sayLoudOrPM(client, "%s (@%s) is not currently online" % (sclient.name, sclient.id))
        else:
            cmd.sayLoudOrPM(client, "You need to provide a Name/DBID: !online <name/dbid>")
    
    # Deals with the !tonline command
    def cmd_tonline(self, data, client, cmd):
        if data:
            input = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if sclient:
                time_online = self.getTimeOnlineByDBID(sclient.id)
                if time_online > 0:
                    cmd.sayLoudOrPM(client, "Client %s (@%s) has been on AR51 servers for %s seconds" % (sclient.exactName, sclient.id, self.secondsToHuman(time_online)))
                else:
                    cmd.sayLoudOrPM(client, "%s (@%s) has not played on our servers" % (sclient.exactName, sclient.id))
        else:
            time_online = self.getTimeOnlineByDBID(client.id)
            cmd.sayLoudOrPM(client, "You have played on our servers for %s" % (self.secondsToHuman(time_online)))
    
    # Deals with the !boob command
    def cmd_boob(self, data, client, cmd):
        last_server = self.getLastServerByDBID(389723)
        if last_server:
            cmd.sayLoudOrPM(client, "Boob is on server %s (%s)" % (last_server["server_name"], last_server["server_ip"]))
        else:
            cmd.sayLoudOrPM(client, "Boob is not currently online")
    
    # Deals with the !noob command
    def cmd_noob(self, data, client, cmd):
        last_server = self.getLastServerByDBID(273192)
        if last_server:
            cmd.sayLoudOrPM(client, "Noob is on server %s (%s)" % (last_server["server_name"], last_server["server_ip"]))
        else:
            cmd.sayLoudOrPM(client, "Noob is not currently online")
    
    # Deals with the !admin or !calladmin command
    def cmd_admin(self, data, client, cmd):
        if data:
            input = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if sclient:
                q = "INSERT INTO shoutbox_shouts (s_mid, s_date, s_message, s_ip, s_edit_history) VALUES (6130, '%s', '%s has reported %s on server %s (%s)', '127.0.0.1', NULL)" % (time.time(), self.console.stripColors(client.name), sclient.exactName, self.console.stripColors(self.server_name), self.server_ip)
        else:
            q = "INSERT INTO shoutbox_shouts (s_mid, s_date, s_message, s_ip, s_edit_history) VALUES (6130, '%s', '%s requires an admin on server %s (%s)', '127.0.0.1', NULL)" % (time.time(), self.console.stripColors(client.name), self.console.stripColors(self.server_name), self.server_ip)
        if self.forumQuery(q):
            cmd.sayLoudOrPM(client, "Admins have been notified")
        else:
            cmd.sayLoudOrPM(client, "Your request couldn't be processed please report to AR51.eu")
    
    # Deals with the !watch command
    def cmd_watch(self, data, client, cmd):
        if data:
            input = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if sclient:
                q = "INSERT INTO watch_list (client_id, client_name, admin_id, admin_name, time_add) VALUES (%i, '%s', %i, '%s', %i)" % (sclient.id, sclient.name, client.id, client.name, time.time())
                self.b3Query(q)
                client.message("Client %s @%s has been added to the watch list" % (sclient.exactName, sclient.id))
        else:
            cmd.sayLoudOrPM(client, "You need to provide a name/CID/DBID: !watch <name/cid/dbid>")
            
    def cmd_gg(self, data, client, cmd):
        self._adminPlugin.sayMany("gg")
        
    def cmd_iplist(self, data, client, cmd):
        if len(self.ip_list) > 0:
            i = 0
            for ip in self.ip_list:
                i += 1
                client.message('^IP: ^7[^2%s^7] %s' % (i, ip))
        else:
            client.message("No IPs loaded")
    
    # --------------------------------------------------------
    #   Helper Functions
    # --------------------------------------------------------
    # Inserts the servers IP & Name into the clients table
    def updateClientJoin(self, client):
        self.debug("Updating client %s server info - joined server" % (client.exactName))
        q = "UPDATE clients SET server_name = '%s', server_ip = '%s' WHERE id = '%s'" % (self.server_name, self.server_ip, client.id)
        self.b3Query(q)
    
    # Updates the clients server IP & name to NULL
    def updateClientQuit(self, client):
        self.debug("Updating client %s server info - quit server" % (client.exactName))
        q = "UPDATE clients SET server_name = NULL, server_ip = NULL WHERE id = '%s'" % (client.id)
        self.b3Query(q)
    
    # Gets the clients last server IP & name by their DBID
    def getLastServerByDBID(self, id):
        q = "SELECT server_name, server_ip FROM clients WHERE id = '%s'" % (id)
        cursor = self.b3Query(q)
        player = cursor.getRow()
        cursor.close()
        if player["server_name"]:
            player["server_name"] = player["server_name"] + "^7"
            return player
        else:
            return False
    
    # Gets the clients time online by their DBID
    def getTimeOnlineByDBID(self, id):
        q = "SELECT time_online FROM clients WHERE id = %s" % (id)
        cursor = self.b3Query(q)
        time_online = cursor.getRow()
        cursor.close()
        return time_online["time_online"]
    
    # Outputs elements from an array
    def outputAR51(self, client, cmd):
        array = self.clients.getClientsByLevel(self.min_level, 100)
        if len(array) > 0:
            tmp = []
            for c in array:
                if c.maskGroup:
                    tmp.append("%s^7 [^3%s^7]" % (c.exactName, c.maskGroup.level))
                else:
                    tmp.append("%s^7 [^3%s^7]" % (c.exactName, c.maxLevel))
            cmd.sayLoudOrPM(client, "Current AR51 members/admins online: " + ", ".join(tmp))
        else:
            self.debug("No AR51 members/admins found")
            cmd.sayLoudOrPM(client, "There are no AR51 members/admins online")
     
    # Checks the players name for the tags
    def checkName(self, client):
        if self.clan_tags.lower() in client.name.lower() and client.maxLevel < self.min_level:
            self._adminPlugin.warnClient(client, self.warn_reason)
            cmd.sayLoudOrPM(client, "^1Please remove our clan tags!")
            # Check again in 30 seconds
            t = threading.Timer(self.warn_interval, self.checkName, (client,))
            t.start()
     
    # Checks if the players IP is in the ban list
    def checkIP(self, client):
        if client.ip in self.ips:
            self.debug("Client %s (@%s) ip %s is in our ban list" % (client.name, client.id, client.ip))
            client.warn("1d", "^1Your IP is in our ban list ...")
     
    # To determine if a player has rage quit or not
    def rageQuit(self, event, client):
        if event == b3.events.EVT_CLIENT_KILL:
            self.debug("Client %s (@%s) has been added to the rage list at %s" % (client.exactName, client.id, int(time.time())))
            self.watch_list[client.id] = int(time.time())
        elif event == b3.events.EVT_CLIENT_DISCONNECT:
            time_taken = time.time() - self.watch_list.get(client.id) # Calc time between getting killed and now (leaving)
            if client.id in self.watch_list and time_taken <= self.rage_interval:
                self.loud("^2%s ^3has ^1RAGE QUIT ^3LOL^7" % (client.exactName))
                self.debug("%s has left within %ss of dying" % (client.exactName, time_taken))
            del self.watch_list[client.id]
            self.debug("Client %s (@%s) has been removed from the list" % (client.name, client.id))
    
    # Updates clients time online
    def timeOnline(self, event, client):
        if self.time_online:
            if event == b3.events.EVT_CLIENT_AUTH:
                self.time_list[client.id] = int(time.time())
            elif event == b3.events.EVT_CLIENT_DISCONNECT:
                time_online = self.getTimeOnlineByDBID(client.id)
                # Add current time spent online
                time_online = ((time.time() - self.time_list[client.id]) + time_online)
                q = "UPDATE clients SET time_online = %i WHERE id = %i" % (time_online, client.id)
                self.b3Query(q)
                self.debug("Updated %s (@%s) time online to %i" % (client.exactName, client.id, time_online))
    
    # Figure out if someone is speccing, and kick if they have been speccing for over afk_time
    def checkSpec(self, client):
        self.debug("Checking %s (@%s) for speccing too long" % (client.name, client.id))
        time = self.afk_list[client.id]
        time = time + 30
        self.afk_list[client.id] = time
        if self.afk_list[client.id] > 15:
            self.debug("Kicking %s (@%s) for being AFK for over %s" % (client.name, client.id, self.afk_time))
            client.kick("^3You have been AFK for too long!")
            del self.afk_list[client.id]
        # Check again in 30 seconds
        t = threading.Timer(30, self.checkSpec, (client,))
        t.start()
    
    # Convert seconds to a readable time duration
    def secondsToHuman(self, t):
        import datetime
        import dateutil.relativedelta
        dt1 = datetime.datetime.fromtimestamp(0)
        dt2 = datetime.datetime.fromtimestamp(int(t))
        rd = dateutil.relativedelta.relativedelta (dt2, dt1)
        return "%dd, %dh, %dm and %ds" % (rd.days, rd.hours, rd.minutes, rd.seconds)
    
    def forumQuery(self, query):
        self.debug("Running a query on Forum: %s" % (query))
        self.forum.query(query)
    
    def b3Query(self, query):
        self.debug("Running a query on B3: %s" % (query))
        return self.query(query)
    
# --------------------------------------------------------
#   Forum Class
# --------------------------------------------------------
class Forum(object):
    """
        Database class that manages the connection, details and any queries
    """
    def __init__(self):
        self.connect()
    
    def connect(self):
        self.db_connect = MySQLdb.connect(host=host, port=port, user=user, passwd=passwd, db=db)
    
    def query(self, query):
        try:
           cursor = self.db_connect.cursor()
           cursor.execute(query)
        except(AttributeError, MySQLdb.OperationalError), e:
           self.error("Exception generated during SQL connection: %s" % (e))
           self.connect()
           cursor = self.db_connect.cursor()
           cursor.execute(query)
        cursor.close()
        return cursor
    
    def __del__(self):
        self.db_connect.close()
        
# --------------------------------------------------------
#   Testing Environment
# --------------------------------------------------------
if __name__ == "__main__":
    # create a fake console which emulates B3
    from b3.fake import fakeConsole, joe, superadmin, simon, reg, moderator, admin
    from b3.config import XmlConfigParser

    conf = XmlConfigParser()
    conf.setXml("""\
<configuration plugin="ar51">
	<!-- General Settings -->
    <settings name="general">
		<!-- The tags that we are checking for (clan name also works) -->
        <set name="clan_tags">AR51</set>
		<!-- Minimum level that is allowed to wear the above tags (everyone below will be warned) - Usually the "members" group (also used for all of the below commands) -->
		<set name="min_level">10</set>
		<!-- Warning reason - Cod colour codes will work -->
		<set name="warn_reason">^3You are not allowed to wear our clan tags!</set>
		<!-- Warning duration -->
		<set name="warn_duration">1h</set>
		<!-- How long until we check the client again -->
		<set name="warn_interval">10</set>
		<!-- Enable rage quit? -->
		<set name="rage_quit">yes</set>
		<!-- Time duration the rage quitter can leave after being killed -->
		<set name="rage_interval">4</set>
		<!-- Enable client server logging? -->
		<set name="server_logging">yes</set>
		<!-- Enable time online logging? -->
		<set name="time_online">yes</set>
		<!-- Enable watch system? -->
		<set name="watch_system">yes</set>
		<!-- Kick AFKers/Spectators? -->
		<set name="kick_afks">yes</set>
		<!-- Time to be AFK/Spec for -->
		<set name="afk_time">300</set>
	</settings>
	<!-- Forum Settings -->
	<settings name="forum">
		<!-- Enable shoutbox shouts? -->
		<set name="db_shouts">no</set>
		<!-- IP/hostname of mysql server -->
		<set name="db_host">127.0.0.1</set>
		<!-- Port of the mysql server -->
		<set name="db_port">3306</set>
		<!-- Username to log into the mysql server -->
		<set name="db_user"></set>
		<!-- Password to use with the user -->
		<set name="db_pass"></set>
		<!-- The forum database -->
		<set name="db_db"></set>
    </settings>
	<!-- IP Ban Settings -->
	<settings name="ipbans">
		<!-- Enable IP Bans? -->
		<set name="ip_bans">yes</set>
		<!-- Level required to add/remove IP bans -->
		<set name="ip_bans_level">80</set>
		<!-- The banned IPs-->
		<ips>
			<ip>0.0.0.0</ip>
			<ip>1.1.1.1</ip>
			<ip>31.51.174.154</ip>
		</ips>
    </settings>
</configuration>


    """)
    
    print("\n\n * * * * * * * * * * * *  Tests starting below * * * * * * * * * * * * \n\n")
    
    myplugin = Ar51Plugin(fakeConsole, conf)
    
    # Initiate emulation
    myplugin.onLoadConfig()
    myplugin.onStartup()
    
    superadmin.connects(cid=0)
    joe.connects(cid=1)
    simon.connects(cid=2)
    reg.connects(cid=3)
    reg.team = b3.TEAM_SPEC
    time.sleep(10)
    superadmin.says("!iplist")
