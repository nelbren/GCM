import yaml
import subprocess
from datetime import datetime


def load_version_config(config_file="version.cfg"):
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"⚠️ Version configuration not found: {config_file}. "
              "It's okay, it's optional.")
        return {}
    except Exception as e:
        print(f"❌ Error reading {config_file}: {e}")
        return {}


def update_version_file(config):
    version_file = config.get("file", "version.txt")
    version_mode = config.get("mode", "manual")
    version = None

    if version_mode == "commits":
        try:
            output = subprocess.check_output(
                ["git", "rev-list", "--count", "HEAD"],
                stderr=subprocess.DEVNULL)
            commit_count = int(output.decode().strip())
            commit_count += 1
            version = f"{commit_count:011,}"
            # version = str(commit_count + 1)
        except Exception as e:
            print(f"⚠️ Error getting number of commits: {e}. "
                  "Or there are no commits.")
            # return None
            commit_count = 1
            version = f"{commit_count:011,}"

    elif version_mode == "date":
        version = datetime.now().strftime("%Y%m%d%H%M%S")

    else:
        return None

    try:
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(version)
        print(f"🆙 Updated version: {version}"
              f" → saved in {version_file}")
    except Exception as e:
        print(f"❌ Error writing {version_file}: {e}")
        return None

    return version
