# fence_hetzner_robot

A very simple fence agent with the same interface of https://github.com/ClusterLabs/fence-agents,
used to fence hetzner root servers using robot apis.

The poweroff fencing action is created by rebooting the server in rescue mode.

The poweron fencing action is created by rebooting the server in rescue mode, the disabling the rescue mode and rebooting it again.


This is a quick&dirty script for a custom oVirt cluster deployed with Hetzner Root servers, tailored for CentOS 7.
To enable it under oVirt, the following actions must be done (assuming an already working oVirt cluster):

* copy fence_hetzner_robot.py /usr/sbin/fence_hetzner_robot
* chmod 0755 /usr/sbin/fence_hetzner_robot
* connect to engine and setup a custom fence agents (tested with oVirt 4.3.4)
  * engine-config -s CustomVdsFenceType="hetzner_robot"
  * engine-config -s CustomVdsFenceOptionMapping="hetzner_robot:ip=server_id"
* reboot the engine to make parameters available on control panel
* under each host power management settings, add a fence agent, choose `hetzner_robot` fence agent from dropdown, and add:
  * Address: your root server main ip address (available from robot webinterface)
  * User Name: robot api username
  * Password: robot api password
  * Options: add `server_id=ip_addr` where ip_addr is the same as Address

This agent does not support status, just on/off/reboot actions (reboot is mapped to on) mainly because hetzner root servers cannot be powered down for real.

