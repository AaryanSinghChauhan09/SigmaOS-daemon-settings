    # SigmaOS-daemon-settings

    Settings daemon (fonts, theme, hotkeys)

    Part of the **SigmaOS** sovereign operating-system ecosystem — a multi-repository
    distribution modelled on Linux Mint and Omarchy Linux. See the parent
    [`SigmaOS`](https://github.com/AaryanSinghChauhan09/SigmaOS) repository for the
    full component index.

    ## Upstream inspirations
    - https://github.com/linuxmint/cinnamon-settings-daemon

    ## Design principles applied
    - **Idempotence**
- **Fail-Fast**
- **Least Astonishment**
- **Information Hiding**
- **KISS**
- **Deterministic Testing**

    ## Usage
    Verbs: `font, theme, hotkey, dump`

    ```
    $ sigma-settingsd font --name "Inter 11" --mono "JetBrains Mono 10" --dpi 96
$ sigma-settingsd theme --gtk Adwaita-dark --icons Papirus --cursor Bibata
$ sigma-settingsd hotkey --binding "<Super>t" --action terminal.launch
$ sigma-settingsd hotkey --list
$ sigma-settingsd dump --format json

    ```

    ## Build & test
    ```
    make build
    make test
    ```

    ## Licence
    GNU General Public License v3.0 (FOSS).
