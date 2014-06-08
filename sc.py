#!/usr/bin/env python3
# coding: utf-8

import os
import argparse

def make_struct(**kwargs):
    return argparse.Namespace(**kwargs)

def load_cfg(py_path):
    res = {}
    if os.path.isfile(py_path):
        with open(py_path) as f:
            txt = f.read()
        exec(txt, {}, res)
    return make_struct(**res)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pkg_path")
    parser.add_argument("egg_fpath")
    args = parser.parse_args()
    
    pkg_path  = os.path.abspath(args.pkg_path)
    egg_fpath = args.egg_fpath

    def make_pkg_path(fname):
        return os.path.join(pkg_path, fname)

    cfg = load_cfg(make_pkg_path("sc.py.cfg"))
    def get_cfg_value(key, def_value=None):
        return getattr(cfg, key, def_value)

    from setuptools import setup, find_packages
    
    name = get_cfg_value("name")
    if not name:
        name = os.path.basename(pkg_path)

    version = get_cfg_value("version")
    if not version:
        import subprocess
        version = subprocess.check_output(["git", "describe", "--tags"], cwd=pkg_path).strip().decode("utf-8")
        
    from pip.req import parse_requirements
    req_fpath = get_cfg_value("requirements")
    if not req_fpath is None:
        if not os.path.isabs(req_fpath):
            req_fpath = make_pkg_path(req_fpath)
        
        install_reqs = parse_requirements(req_fpath)
        reqs = [str(ir.req) for ir in install_reqs]
    else:
        reqs = []

    py_modules = []
    for fname in os.listdir(pkg_path):
        import re
        m = re.match("(.*)\.py$", fname)
        if m:
            py_modules.append(m.group(1))
            
    orig_df = get_cfg_value("data_files", [])
            
    # setuptools

    # :TRICKY: sourceless пакеты должны содержать просто .pyc/.pyo-файлы, без
    # всяких __pycache__ и т.д. => меняем функцию (хак?)
    # :TODO: как минимум добавить вариант с .pyo
    def cache_from_source(path, debug_override=None):
        return path + "c"
    import imp
    imp.cache_from_source = cache_from_source
    
    # :TRICKY: приходится менять путь
    old_dir = os.getcwd()
    os.chdir(pkg_path)
    
    df_lst = []
    def append_file(dname, fname):
        df_lst.append((dname, [fname]))
    for fname in orig_df:
        if os.path.isdir(fname):
            for d, d2, ff in os.walk(fname):
                for f in ff:
                    append_file(d, os.path.join(d, f))
        else:
            append_file(os.path.split(fname)[0], fname)

    dist = setup(
        name = name,
        version = version,
        install_requires=reqs,
        
        packages = find_packages(),
        py_modules = py_modules,
        # влияет на MANIFEST.in - реально добавятся в .egg только при True
        # (для sdist будут присутствовать в любом случае) и в случае, если эти
        # файлы идут в составе соответ. пакета (см. параметр packages), черт
        include_package_data = True,
        
        # заполняет файл .egg-info/entry_points.txt, с тем чтобы
        # при установке создать соответ. скрипт
        entry_points = {
            'console_scripts': get_cfg_value("console_scripts", []),
        },
        
        script_args = ["bdist_egg", "--exclude-source-files"],
        
        data_files = df_lst,
        
        # остальное
        script_name = '', # :KLUDGE: без setup.py (но warning остается)
    )
    
    orig_egg_fpath = None
    for dist_file in dist.dist_files:
        if dist_file[0] == "bdist_egg":
            orig_egg_fpath = dist_file[2]
            break
    assert orig_egg_fpath
    orig_egg_fpath = os.path.abspath(orig_egg_fpath)

    os.chdir(old_dir)
    
    import shutil
    shutil.copy(orig_egg_fpath, egg_fpath)
    
    
    