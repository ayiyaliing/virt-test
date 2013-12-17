import os, logging
import commands
from virttest import data_dir
def mount_nfs(src, dst):
	cmd = "mount %s %s -o ro" % (src, dst)
	if os.system("mount | grep %s" % src):
		logging.info("the nfs don't be mount, going....")
		s, o = commands.getstatusoutput(cmd)
		if s != 0:
			logging.error("Fail to mount nfs")
	else:
		logging.info("ISO nfs have already mounted")
		


def run_image_copy(test, params, env):

	logging.info("***************************************************")
	mount_point = '/tmp/images'
	if not os.path.exists(mount_point):
		os.mkdir(mount_point)
	#10.66.8.128:/vol/image/	
	remote_server = params.get('local_image_nfs_server')
	#/virt-test/shared/nfs-image
	#remote_dir = paramas.get('local_image_dir')
	base_dir = data_dir.get_data_dir()
	remote_dir = os.path.join(base_dir, 'nfs_image/')
	logging.info("the base_dir is %s, the remote_dir is %s", base_dir, remote_dir)
'''
	remote_image = params.get('image_name') + '.vmdk'
	
	mount_nfs(remote_server, mount_point)
	
	src_path = os.path.join(mount_point, remote_image)
	dst_path = os.path.join(remote_dir, remote_image)
	
	cmd = "cp %s %s" %(src_path, dst_path)
	s, o = commands.getstatusoutput(cmd)
	if s!=0:
		logging.error("fail to copy the image")
	else:
		logging.info("cp the image successfully")
'''	

