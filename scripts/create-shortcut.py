"""Create desktop shortcut for BrandPulse VIS"""
import os
import win32com.client

desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
shortcut_path = os.path.join(desktop, 'BrandPulse VIS.lnk')
cmd_path = r'D:\robin-skills\trae solo\brand-pulse-vis\launch-brandpulse.cmd'
icon_path = r'D:\robin-skills\trae solo\brand-pulse-vis\favicon.ico'
work_dir = r'D:\robin-skills\trae solo\brand-pulse-vis'

shell = win32com.client.Dispatch('WScript.Shell')
shortcut = shell.CreateShortcut(shortcut_path)
shortcut.TargetPath = cmd_path
shortcut.IconLocation = f'{icon_path}, 0'
shortcut.WorkingDirectory = work_dir
shortcut.Description = 'BrandPulse VIS - 视觉信号追踪'
shortcut.Save()

print(f'Shortcut created: {shortcut_path}')
print(f'Target: {cmd_path}')
print(f'Icon: {icon_path}')
