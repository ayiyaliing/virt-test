#!/usr/bin/python

import os, sys, re
import logging, time,commands
from virttest import remote
from pysphere import VIServer

class ESX_config(object):
	def __init__(self):
		self.defaultOpt = {}
		self.opts = self.defaultOpt
		self.allconfigOpt=[
		".encoding",
		"config.version",
		"virtualName",
		"displayName",
		"scsi0.present",
		"scsi0.virtualDev",
		"memsize",
		"scsi0.0.present",
		"scsi0.0.fileName",
		"ide1.0.present",
		"ide1.0.deviceType",
		"ide1.0.startConnected",
		"ide1.0.filename",
		"guestOS",
		"virtualHW.productCompatibility",
		"ethernet0.present",
		"ethernet0.virtualDev",
		"ethernet0.networkName",
		"pciBridge0.present",
		"pciBridge0.virtualDev",
		"pciBridge1.present",
		"pciBridge1.virtualDev",
		"floppy0.fileType",
		"floppy0.fileName",
		"floppy0.clientDevice",
		"bios.forceSetupOnce",
		"bios.bootOrder"]

	def setopt(self, name, value):
		"""set an option in the config"""
		self.opts[name] = value
	def getopt(self, name):
		return self.opts[name]
        def cmp_opt(self, opt1, opt2):
        	if opt1 in self.allconfigOpt and opt2 in self.allconfigOpt:
            		i1 = self.allconfigOpt.index(opt1)
            		i2 = self.allconfigOpt.index(opt2)
            		return i1-i2
        	else:
            		return 0

	def to_string(self):
	#	opt_list = self.opts.items()
		opt_list = sorted(self.opts.items(),
            		key=lambda d:d[0],
            		cmp=lambda x,y:self.cmp_opt(x,y))
		print "----the opt_list is %s----" % opt_list
		string = "# ESX configuration by esx virt-test\n"
		for k, v in opt_list:
#	            if isinstance(v, int):
#        	        piece = "%s = %i" % (k, v)
#           	    elif isinstance(v, list) and v:
#              		piece = "%s = %s" % (k, v)
#            	    if isinstance(v, str) and v:
                    piece = "%s = \"%s\"" % (k, v)
#                    else:
#                        piece = None

                    if piece:
                       string += "%s\n" % piece

		return string

		
	def write(self,filename):
		output = file(filename, 'w')
		output.write(self.to_string())
		output.close()
		
	def __str__(self):
	    filename = "/root/virt-test/shared/data/vmx/vm.vmx"
	    self.write(filename)
            return filename
class ESXdomain(object):
	
	def __init__(self, name, params):
		self.name = name
		self.params = params
		self.config = None
		self.remote_ip = self.params.get("remote_esx", "none")
		self.remote_passwd = self.params.get("remote_passwd", "123qweP")
		self.guest_dir = None
		self.vm_path = None
		self.vm1 = None
		self.server = VIServer()
		self.login_VI()

	def create(self):
		config = self.make_config()
		#print "the config is %s" % config
		self.config = config
		print "~~~~~~~~~~~~~~~~~%s \n" % self.config
		self.login()
		self.check_esx_nfs_storage()
		if self.params.get('type') == 'esx_unattended':
			self.create_esx_image()
		else:
			logging.info("no need to create the esx image, pass")
		self.reday_vmxfile()
		if self.params.get('type') == "esx_unattended":
			self.ready_floppy_iso()
		#self.start_vm()
		self.register_vm()
		self.init_vm()
		self.start_vm_sphere()
	def login_VI(self):
		self.con =  self.server.connect(self.remote_ip, "root", self.remote_passwd)
		if not self.con:
			logging.info("login the ESX server!")
		else:
			logging.error("fail to login the ESX Server!")	
		
		
	def login(self):		
    		#remote_ip = self.params.get("remote_esx", "none")
    		#remote_passwd = self.params.get("remote_passwd", "123qweP")
		cmd = "ls"
		l_status, l_output = self.remote_ssh(cmd, self.remote_ip, self.remote_passwd)
		if l_status == 0:
			logging.info("Esx auto login successfully")
		else:
			logging.error("Fail to login, please check your environment!")
		#self.remote_ip = remote_ip
		#self.remote_passwd = remote_passwd

	def check_esx_nfs_storage(self):
		cmd = "esxcfg-nas -l"
		l_status, l_output = self.remote_ssh(cmd, self.remote_ip, self.remote_passwd)
		if l_output.find("virt-test-nfs") != -1 and l_output.find("unavailable") != -1:
			cmd = "esxcfg-nas -d %s" % (self.params.get('esx_nfs_mount')) 
			status, output = self.remote_ssh(cmd, self.remote_ip, self.remote_passwd)
			logging.info("umount the esx nfs storage successfully!")
		elif l_output.find("virt-test-nfs") == -1:
			cmd = "esxcfg-nas -a -o %s -s /var/lib/virt_test %s" % (self.params.get('local_ip'), self.params.get('esx_nfs_mount'))
			status, output = self.remote_ssh(cmd, self.remote_ip, self.remote_passwd)
			if status == 0:
				logging.info("esx storage mount successfully!")
			else:
				logging.error("fail to mount, pls check it!")
		elif l_output.find("unavailable") != -1:
			logging.info("waiting to be solve~~~~")
		else:
			pass

	def create_esx_image(self):
		remote_dir = "/vmfs/volumes/datastore1*/"
		guest_name = self.params.get('displayName')
		cmd = "cd %s; rm -rf %s; mkdir -p %s" % (remote_dir, guest_name, guest_name)
		logging.info("Create esx guest work directory %s/%s", remote_dir, self.params.get('displayName'))
		dir_status, dir_output = self.remote_ssh(cmd, self.remote_ip, self.remote_passwd)
		if dir_status ==  0:
			logging.info("esx guest dir create successfully!")
		else:
			logging.error("fail to create the guest dir!")
		self.guest_dir = remote_dir + guest_name
		cmd = "cd %s; vmkfstools -c 15G -a pvscsi `pwd -P`/%s.vmdk" % (self.guest_dir, self.params.get('displayName'))
		logging.info("Create esx guest images")
		disk_status, disk_output = self.remote_ssh(cmd, self.remote_ip, self.remote_passwd)
		if disk_status == 0:
			logging.info("Create the esx image successfully")
		else:
			logging.error("Fail to create esx image")

	def reday_vmxfile(self):
		#modify this method with regular to generate the vmx file
		fd = file('/root/virt-test/shared/data/vmx/vm.vmx', 'r')
        	list_dect = []
        	list_src = fd.readlines()
        	for i in list_src:
                	if len(re.findall(r'^ide[0-9]\.', i)):
                        	re_i =  i.replace('.', ':', 1)
                        	list_dect.append(re_i)
                	elif len(re.findall(r'^scsi[0-9]\.[0.9]', i)):
                        	si_i = i.replace('.', ':', 1)
                        	list_dect.append(si_i)
                	else:
                        	list_dect.append(i)
		right_name = '/root/virt-test/shared/data/vmx/' + self.name +'.vmx'
        	fd2 = file(right_name, 'w')
        	fd2.writelines(list_dect)
        	fd.close()
        	fd2.close()

        	cmd = "cd %s; cp ../../%s/vmx/%s.vmx ." % (self.guest_dir, self.params.get('esx_nfs_mount'), self.name)
		vmx_status, vmx_output = self.remote_ssh(cmd, self.remote_ip, self.remote_passwd)
		if vmx_status == 0:
			logging.info("the vmx is moved the right directory successfully")
		else:
			logging.error("the vmx fail to change!")

	def ready_floppy_iso(self):
		cp_cmd = "cp %s %s" % ("/root/virt-test/shared/data/nfs/ISO/RHEL-Server-6.4/64/RHEL6.4-20130130.0-Server-x86_64-DVD1-ks.iso", "/root/virt-test/shared/data/isos/rhel6-5.iso")
		s, o = commands.getstatusoutput(cp_cmd)
		if s != 0:
			logging.error("fail to cp")
		else:
			logging.info("copy successful")		

		iso_name = self.params.get('cdrom_cd1').rsplit('/', 1)[1]
        	flp_name = self.params.get('floppy_name').rsplit('/', 1)[1]
            	# /nfs-9-84/esx_virtest_auto/shared/data/isos/linux/RHEL-6.4-x86_64-DVD.iso
        	remote_cmd = "cd %s; ln -s ../../%s/isos/%s %s; ln -s ../../%s/%s %s" % (self.guest_dir, self.params.get('esx_nfs_mount'), iso_name, iso_name, 
                                                                                self.params.get('esx_nfs_mount'), self.params.get('floppy_name'), flp_name)
        	logging.info("Prepare iso and floppy images: %s, %s", iso_name, flp_name)
        	ln_status, ln_output = self.remote_ssh(remote_cmd, self.remote_ip, self.remote_passwd)
        	logging.info("Status:%s", ln_status)
        	logging.info("Output:\n%s", ln_output)

	def start_vm(self):
		#with pysphere to start vm
		start_cmd = "cd %s; vnum=`vim-cmd solo/registervm %s/%s.vmx`; vim-cmd vmsvc/power.on $vnum" % (self.guest_dir, self.guest_dir, self.name)
		start_status, start_output = self.remote_ssh(start_cmd, self.remote_ip, self.remote_passwd)
		if start_status == 0:
			logging.info("the vm start successfully")
		else:
			logging.error("fail to start vm!")		
	def register_vm(self):
		#with pysphere to start vm
		start_cmd = "cd %s; vnum=`vim-cmd solo/registervm %s/%s.vmx`" % (self.guest_dir, self.guest_dir, self.name)
		start_status, start_output = self.remote_ssh(start_cmd, self.remote_ip, self.remote_passwd)
		if start_status == 0:
			logging.info("register vm successfully")
		else:
			logging.error("fail to register vm!")		
	def init_vm(self):
		self.vm_path = self.get_vm_path()
		self.vm1 = self.server.get_vm_by_path(self.vm_path)
	def start_vm_sphere(self):
		if not self.vm1.power_on():
			logging.info("the vm start successfully")
		else:
			logging.info("fail to start vm")
		
	def stop_vm(self):
		if not self.vm1.power_off():
			logging.info("power off the vm successfully")
		else:
			logging.info("fail to power off vm")
	def reset_vm(self):
		pass
	def get_vm_status(self):
		status = self.vm1.get_status()
		return status		
	def get_vm_path(self):
		vmlist = self.server.get_registered_vms()
		for vm_item in vmlist:
			if vm_item.rsplit('/', 1)[1].split('.')[0] == self.name.split('.')[0]:
				return vm_item
		

	def remote_ssh(self, cmd, ip, passwd):
		session = remote.remote_login("ssh", ip, "22", "root", passwd, "#")
		time.sleep(3)
		status, output = session.cmd_status_output(cmd, internal_timeout=10)
		time.sleep(3)
		session.close()
		return int(status), output
	

	def make_config (self,name=None, params=None):
		if name is None:
			name = self.name
		c = ESX_config()
		#c.setopt('displayName',name)
		
	        allconfig = c.allconfigOpt
	        for a in allconfig:
            		setattr(self, a, self.params.get(a, ''))
		for b in allconfig:
			c.setopt(b, getattr(self, b))
		return c
#  for b in self.attributes_demo:
#            self.params[b] = getattr(self, b)
	def __delete__(self):
		server.disconnect()


if __name__ == "__main__":
	c = ESX_config()
	opts = {".encoding"            :  "UTF-8",
            	"config.version"       :  "8",
           	"displayName"          :  "vm1",
           	"memsize"              :  "1024",
            	"scsi0.present"        :  "TRUE",
            	"scsi0.fileName"       :  "jingli-esx-auto.vmdk",
            	"ide1:0.present"       :  "TRUE",
            	"ide1:0.deviceType"    :  "cdrom-image",
            	"ide1:0.startConnected"       : "TRUE",
            	"ide1.fileName"        :  "/vmfs/volumes/521ea6b6-feccccf2-fed5-90b11c459463/rhel6.5.iso",
            }
	for (k, v) in opts.items():
		print k, v 
		c.setopt(k, v)
	print c
#	print make_config('zhuangha')
	d = ESXdomain()
	print d.make_config('kjk')
