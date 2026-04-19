import os
import json
import yaml
from datetime import datetime
from utils import check_output_git


def safe_print(message):
    try:
        print(message)
    except UnicodeEncodeError:
        fallback = message.encode("ascii", errors="ignore").decode("ascii")
        print(fallback or "[message could not be displayed in this terminal]")


def load_version_config(config_file="version.cfg"):
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        safe_print(f"⚠️ Version configuration not found: {config_file}. "
                   "It's okay, it's optional.")
        return {}
    except Exception as e:
        safe_print(f"❌ Error reading {config_file}: {e}")
        return {}


def generate_version_badge(version, badge_dir=".badges"):
    try:
        os.makedirs(badge_dir, exist_ok=True)
        badge_content = {
            "schemaVersion": 1,
            "label": "version",
            "message": version,
            "color": "blue"
        }
        badge_file = os.path.join(badge_dir, "version.json")

        with open(badge_file, "w", encoding="utf-8") as f:
            json.dump(badge_content, f, ensure_ascii=False, indent=2)

        safe_print(f"🏷️ Badge created: {badge_file}")

    except Exception as e:
        safe_print(f"❌ Error creating badge: {e}")


def update_version_file(config):
    version_file = config.get("file", "version.txt")
    version_mode = config.get("mode", "manual")
    version = None

    if version_mode == "commits":
        try:
            output = check_output_git(
                ["rev-list", "--count", "HEAD"],
                stderr=None
            )
            commit_count = int(output.decode().strip())
            commit_count += 1
            version = f"{commit_count:011,}"
            # version = str(commit_count + 1)
        except Exception as e:
            safe_print(f"⚠️ Error getting number of commits: {e}. "
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
        safe_print(f"🆙 Updated version: {version}"
                   f" → saved in {version_file}")
    except Exception as e:
        safe_print(f"❌ Error writing {version_file}: {e}")
        return None

    if os.path.isdir(".badges"):
        generate_version_badge(version)

    return version
