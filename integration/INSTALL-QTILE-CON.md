# Integrate with Qtile-Con

1. Install this settings application as the same user that runs Qtile:

   ```sh
   cd qtile-settings
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -e .
   ```

   Keep the virtual environment activated when testing. For a command available in normal Qtile sessions, install it with `pipx install .` (or `pipx install --system-site-packages .` if using distro-provided PySide6) instead.

2. Open `~/.config/qtile/qtile_config/settings.py` and confirm that your modular Qtile-Con configuration is installed there.

3. Merge the two keybindings from `qtile-con-keys-snippet.py` into the existing `keys` list in `Qtile-con/qtile_config/keys.py`. The app opens with **Super+S**; quick settings opens with **Super+Shift+S**. Check that these shortcuts do not conflict with your own bindings.

4. Validate and restart Qtile:

   ```sh
   qtile check -c ~/.config/qtile/config.py
   ```

   Then use **Super+Ctrl+R** to restart Qtile.

The GUI edits the installed configuration in `~/.config/qtile`, not the Git checkout. It makes timestamped backups before writes. Copy reviewed changes back to your repository and commit them when you want them version-controlled.
