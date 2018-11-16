import os
import ctypes
import platform
import _winreg

from .winstructures import *


class disable_fsr():
	"""
	A class to disable file system redirection
	"""
	disable = ctypes.windll.kernel32.Wow64DisableWow64FsRedirection
	revert = ctypes.windll.kernel32.Wow64RevertWow64FsRedirection

	def __enter__(self):
		self.old_value = ctypes.c_long()
		self.success = self.disable(ctypes.byref(self.old_value))

	def __exit__(self, type, value, traceback):
		if self.success:
			self.revert(self.old_value)


class payloads():
	"""
	Checks if payload exists on disk and if the
	file extension is correct
	"""
	def exe(self, payload):
		if os.path.isfile(os.path.join(payload)) and payload.endswith(".exe"):
			return True
		else:
			# Check if payload is a bin with args (e.g C:\\Windows\\System32\\cmd.exe /k whoami)
			p = payload.split(' ', 1)[0]
			if os.path.isfile(p):
				return True

			return False

	def dll(self, payload):
		if os.path.isfile(os.path.join(payload)) and payload.endswith(".dll"):
			return True
		else:
			return False


class process():
	"""
	A class to spawn, elevate or terminate processes
	"""
	def create(self, payload, params='', window=False):
		shinfo = ShellExecuteInfoW()
		shinfo.cbSize = sizeof(shinfo)
		shinfo.fMask = SEE_MASK_NOCLOSEPROCESS
		shinfo.lpFile = payload
		shinfo.nShow = SW_SHOW if window else SW_HIDE
		shinfo.lpParameters = params

		if not ShellExecuteEx(byref(shinfo)):
			return False
		else:
			return True

	def runas(self, payload, params=''):
		shinfo = ShellExecuteInfoW()
		shinfo.cbSize = sizeof(shinfo)
		shinfo.fMask = SEE_MASK_NOCLOSEPROCESS
		shinfo.lpVerb = "runas"
		shinfo.lpFile = payload
		shinfo.nShow = SW_SHOW
		shinfo.lpParameters = params
		try:
			if ShellExecuteEx(byref(shinfo)):
				return True
			else:
				return False
		except Exception as error:
			return False

	def enum_processes(self):
		size            = 0x1000
		cbBytesReturned = DWORD()
		unit            = sizeof(DWORD)
		dwOwnPid        = os.getpid()
		while 1:
			process_ids = (DWORD * (size // unit))()
			cbBytesReturned.value = size
			EnumProcesses(byref(process_ids), cbBytesReturned, byref(cbBytesReturned))
			returned = cbBytesReturned.value
			if returned < size:
				break
			size = size + 0x1000
		process_id_list = list()
		for pid in process_ids:
			if pid is None:
				break
			if pid == dwOwnPid and pid == 0:
				continue
			process_id_list.append(pid)
		return process_id_list

	def enum_process_names(self):
		pid_to_name = {}
		for pid in self.enum_processes():
			name = False
			try:
				process_handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
			except Exception as e:
				continue
			name = get_process_name(process_handle)
			if name:
				pid_to_name[pid] = name
			if process_handle:
				CloseHandle(process_handle)
		return pid_to_name

	def get_process_pid(self, processname):
		pid_to_name = self.enum_process_names()
		for pid in pid_to_name:
			if pid_to_name[pid].lower().find(processname) != -1:
				return pid

	def terminate(self, processname):
		pid = self.get_process_pid(processname)
		if pid:
			try:
				phandle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
				os.kill(pid, phandle)
				return True
			except:
				pass
		return False


class information():
	"""
	A class to handle all the information gathering
	"""
	def system_directory(self):
		return os.path.join(os.environ.get('windir'), 'system32')
			
	def windows_directory(self):
		return os.environ.get('windir')
			
	def architecture(self):
		return platform.machine()

	def admin(self):
		if ctypes.windll.shell32.IsUserAnAdmin() == True:
			return True
		else:
			return False

	def build_number(self):
		try:
			key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, os.path.join(
				"Software\\Microsoft\\Windows NT\\CurrentVersion"), 0, _winreg.KEY_READ)
			cbn = _winreg.QueryValueEx(key, "CurrentBuildNumber")
			_winreg.CloseKey(key)
		except Exception as error:
			return False
		else:
			return cbn[0]

	def uac_level(self):
		try:
			key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, os.path.join(
				"Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System"), 0, _winreg.KEY_READ)
			cpba = _winreg.QueryValueEx(key, "ConsentPromptBehaviorAdmin")
			cpbu = _winreg.QueryValueEx(key, "ConsentPromptBehaviorUser")
			posd = _winreg.QueryValueEx(key, "PromptOnSecureDesktop")
			_winreg.CloseKey(key)
		except Exception as error:
			return False

		if (cpba[0] == 0) and (cpbu[0] == 3) and (posd[0] == 0):
			return 1
		elif (cpba[0] == 5) and (cpbu[0] == 3) and (posd[0] == 0):
			return 2
		elif (cpba[0] == 5) and (cpbu[0] == 3) and (posd[0] == 1):
			return 3
		elif (cpba[0] == 2) and (cpbu[0] == 3) and (posd[0] == 1):
			return 4
		else:
			return False