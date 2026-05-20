from lldb import SBDebugger, SBStringList, SBType  # pyright: ignore[reportMissingModuleSource]
from typing import Dict, Any

def is_rust_type(sbtype: SBType, internal_dict: Dict[str, Any]) -> bool:
    kind = internal_dict['lldb_lookup'].classify_rust_type(sbtype)
    return kind != 'Other'

def print_message(message: str):
    print(f"Rust language visualizer installer: {message}")


def get_env_from_sbstringlist(list: SBStringList, to_merge: dict[str, str] | None = None) -> dict[str, str]:
    if to_merge is None:
        to_merge = {}
    environment: dict[str, str] = to_merge.copy()
    entry: str
    for entry in list:
        key, value = entry.split('=', 1)
        environment[key] = value
    return environment

def get_working_dir_and_environment(debugger: SBDebugger) -> tuple[str | None, dict[str, str] | None]:
    import os
    working_dir: str | None = None
    environment: dict[str, str] = os.environ.copy()
    
    target = debugger.GetSelectedTarget()
    platform = debugger.GetSelectedPlatform()
    launch_info = None
    if target and target.IsValid():
        platform = target.GetPlatform()
        launch_info = target.GetLaunchInfo()
    if platform:
        working_dir = platform.GetWorkingDirectory()
        environment = get_env_from_sbstringlist(platform.GetEnvironment().GetEntries(), environment)
    if launch_info:
        working_dir = launch_info.GetWorkingDirectory()
        environment = get_env_from_sbstringlist(launch_info.GetEnvironment().GetEntries(), environment)

    return working_dir, environment

def install_rust_visualizers(debugger: SBDebugger, internal_dict):
    # try to install the rust visualizers; if the category "Rust" already exists, or if we're able to import "codelldb", don't do anything
    rust_category = debugger.GetCategory("Rust")
    if rust_category and (rust_category.GetNumSummaries() > 0 or rust_category.GetNumSynthetics() > 0):
        print_message("Rust category already exists, skipping installation")
        return
    try:
        import codelldb
        print_message("codelldb imported, skipping installation")
        return
    except ImportError:
        pass
    import subprocess
    from os import path

    try:
        version = debugger.GetVersionString()
        version_major = int(version[version.find('version ') + 8:].split('.')[0])
    except Exception:
        version_major = 0

    command = ['rustc', '--print=sysroot']

    try:
        working_dir, environment = get_working_dir_and_environment(debugger)

        si = None
        if hasattr(subprocess, 'STARTUPINFO'):
            si = subprocess.STARTUPINFO(dwFlags=subprocess.STARTF_USESHOWWINDOW,  # type: ignore
                                        wShowWindow=subprocess.SW_HIDE)  # type: ignore
        sysroot = subprocess.check_output(command, startupinfo=si, encoding='utf-8', cwd=working_dir, env=environment).strip()

        formatters = path.join(sysroot, 'lib/rustlib/etc')
        lldb_lookup = path.join(formatters, 'lldb_lookup.py')
        lldb_providers = path.join(formatters, "lldb_providers.py")
        lldb_rust_types = path.join(formatters, "rust_types.py")
        lldb_commands = path.join(formatters, 'lldb_commands')
        if not path.isfile(lldb_lookup):
            if sysroot:
                print_message('Could not find LLDB data formatters in your Rust toolchain.  For more information, please visit https://github.com/vadimcn/codelldb/wiki/Windows')
            else:
                print_message("Could not find sysroot")
            return
        debugger.HandleCommand(command="command script import '{}'".format(lldb_lookup))
        debugger.HandleCommand(command="command script import '{}'".format(lldb_providers))
        debugger.HandleCommand(command="command script import '{}'".format(lldb_rust_types))
        use_recognizer_fn = version_major >= 19 and hasattr(internal_dict['lldb_lookup'], 'classify_rust_type')
        with open(lldb_commands, 'rt') as f:
            for line in f:
                if use_recognizer_fn and line.startswith('type synthetic') and '-x ".*"' in line:
                    # Replace wildcard matching with a recognizer function so Rust synthetics do not get attached
                    # to types we do not intend to handle, such as ints or floats.
                    line = 'type synthetic add -l lldb_lookup.synthetic_lookup --recognizer-function rust_lang_support.is_rust_type --category Rust'
                debugger.HandleCommand(line.strip())
        print_message("Installed successfully!")

    except Exception as e:
        print_message(f"Error initializing Rust sysroot: {e}")
        return

def __lldb_init_module(debugger: SBDebugger, dict):
    install_rust_visualizers(debugger, dict)
