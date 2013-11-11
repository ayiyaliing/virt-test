import logging
def run_uptime(test, params, env):
	"""
	Docstring describing uptime
	"""	
	vm = env.get_vm(params["main_vm"])
	logging.info("----------------------------------------------------------")
	vm.verify_alive()
	logging.info("----------------------------------------------------------")
	timeout = float(params.get("login_timeout", 240))
	session = vm.wait_for_login(timeout=timeout)
	uptime = session.cmd('uptime')
	logging.info("Guest uptime result is: %s", uptime)
	session.close()	
