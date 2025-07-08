import os
import platform
from pathlib import Path


def ensure_cmdrc_has_alias(script_path):
    script_dir = os.path.dirname(script_path)
    user_profile = os.environ["USERPROFILE"]
    cmdrc_path = os.path.join(user_profile, "cmdrc.bat")
    alias_line = f'doskey gcm="{script_dir}\\run.bat"'

    if os.path.exists(cmdrc_path):
        with open(cmdrc_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if any(alias_line in line for line in lines):
            print("✔️ Alias 'gcm' ya configurado en cmdrc.bat.")
            return
    with open(cmdrc_path, "a", encoding="utf-8") as f:
        f.write("\n" + alias_line + "\n")
    print("✅ Alias 'gcm' agregado a cmdrc.bat.")
    print("\n📌 Recuerda editar tu acceso directo al CMD para que use:")
    print('   %comspec% /k "%USERPROFILE%\\cmdrc.bat"')


def ensure_bash_alias(script_path, env):
    script_dir = os.path.dirname(script_path)
    if env == "CYGWIN":
        script_path = script_path.replace('\\', '\\\\\\\\')
        script_dir = script_dir.replace('\\', '\\\\\\\\')
    home = os.environ.get('HOME', '')
    if home:
        home = Path(home)
    else:
        home = Path.home()
    bashrc_path = home / ".bashrc"

    alias_line = f'alias gcm="{script_dir}/run.bash"'

    if bashrc_path.exists():
        content = bashrc_path.read_text(encoding="utf-8")
        if alias_line in content:
            print("✔️ Alias 'gcm' ya configurado en .bashrc.")
        else:
            with open(bashrc_path, "a", encoding="utf-8", newline='\n') as f:
                f.write("\n" + alias_line + "\n")
            print("✅ Alias 'gcm' agregado a .bashrc.")

    if env == "MACOS":
        profiles = ['.zprofile', '.bash_profile']
        for profile in profiles:
            profile_path = home / profile
            if profile_path.exists():
                content = profile_path.read_text(encoding="utf-8")
                if alias_line in content:
                    print(f"✔️ Alias 'gcm' ya configurado en {profile}.")
                else:
                    with open(profile_path, "a", encoding="utf-8",
                              newline='\n') as f:
                        f.write("\n" + alias_line + "\n")
                    print(f"✅ Alias 'gcm' agregado a {profile}.")


def detect_environment():
    system = platform.system().lower()
    term = os.environ.get('TERM', '').lower()
    shell = os.environ.get('SHELL', '').lower()
    msystem = os.environ.get('MSYSTEM', '').lower()
    ostype = os.environ.get('OSTYPE', '').lower()

    if 'darwin' in ostype or system == 'darwin':
        return 'MACOS', '🍎'
    elif 'linux' in ostype or system == 'linux':
        return 'LINUX', '🐧'
    elif 'cygwin' in ostype or 'cygwin' in term or 'cygwin' in shell:
        return 'CYGWIN', '🪟'
    elif 'msys' in ostype or 'mingw' in ostype or 'mingw' in msystem:
        return 'GIT BASH', '🪟'
    elif system == 'windows':
        return 'CMD', '🪟'
    else:
        return 'UNKNOWN', '❓'


if __name__ == "__main__":
    script_path = os.path.abspath("gcm.py")
    env, emoji = detect_environment()
    print(f"Detected environment: {env}")

    if env == "CMD":
        ensure_cmdrc_has_alias(script_path)
    elif env in ("LINUX", "MACOS", "CYGWIN", "GIT BASH"):
        ensure_bash_alias(script_path, env)
    else:
        print(f"⚠️ Sistema operativo {env}{emoji} "
              "no soportado automáticamente.")
