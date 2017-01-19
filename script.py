#!/usr/bin/python -E
"""ASML Linux Patch Tooling"""

__author__ = "FC-024 Computer Systems Software Lifecycle"
__version__ = "1.32"
__date__ = "2016-12-01"

import os
import re
import sys
import json
import atexit
import shutil
import logging
import tarfile

sys.path.append('/usr/lib')
import asml_patch as lpt
# Refrain from writing .pyc or .pyo files
sys.dont_write_bytecode = True

SPC_PATTERNS = ("servicepc", "srvh")


def get_naming_convention(fname):
    if re.search(shared.conf.get('match', 'patches'), fname):
        return 'old'
    elif re.search(shared.conf.get('match', 'new_patches'), fname):
        return 'new'
    else:
        return None


def set_naming_convention(id_rpm, shared):
    if get_naming_convention(id_rpm):
        shared.naming_convention = get_naming_convention(id_rpm)
        shared.id_rpm = id_rpm
        return True
    else:
        return False


def set_patchname(shared):
    set_name_version_indx(shared)
    msg = "{mode}: nameverindx: {indx}".format(mode=shared.mode,
                                               indx=shared.name_version_indx)
    shared.logger.console.debug(msg)
    nvi_list = []
    for indx, item in enumerate(shared.name_version_indx):
        if item is None:
            item = ''
        nvi_list.append(item)
    patch_name = nvi_list[0]
    promo = nvi_list[-1]
    if promo not in ('c', 'b',):
        patch_name += promo
        if nvi_list[1]:
            patch_name += '-' + nvi_list[1]
    shared.patchname = patch_name


def validate_patch(data_container):
    """
    Pre-Check the data-container in-memory for an rpm-file that conforms to the
    new or old naming conventions (D000471562).
    """
    shared.logger.console.debug("Validating Patch...")
    # Path to check for already extracted patch
    extract_path = shared.conf.get('path', 'extract')
    extract_dir = os.path.join(extract_path,
                               data_container.split(os.path.sep)[-1])
    msg = "{mode}: {ext}".format(mode=shared.mode, ext=extract_dir)
    shared.logger.console.debug(msg)

    is_tar = False
    try:
        if tarfile.is_tarfile(data_container):
            is_tar = True
    except IOError as e:
        pass

    if os.path.exists(extract_dir) and not is_tar:
        msg = "{mode}: {dc}".format(mode=shared.mode, dc=data_container)
        shared.logger.console.debug(msg)
        file_name = os.path.basename(data_container.rstrip('/'))
        if not set_naming_convention(file_name, shared):
            msg = "WRONG Patch found in {extract}".format(extract=extract_dir)
            shared.logger.console.debug(msg)
            return False
        else:
            set_patchname(shared)
            return True

    if not os.path.exists(data_container):
        return False

    success_flag = False
    if os.path.isdir(data_container):
        shared.logger.console.debug("Patch found in Directory")
        for lsfile in os.listdir(data_container):
            full_path = os.path.join(data_container, lsfile)
            if lpt.is_rpm(full_path):
                fname = lsfile.split(os.path.sep)[-1]
                if set_naming_convention(fname, shared):
                    # shared.id_rpm_contents = lpt.rpm2cpio(open(full_path, 'r'))
                    if shared.mngr:
                        set_patchname(shared)
                        path = os.path.join(extract_dir)
                        shared.logger.console.debug("Copying Patch to: {0}".format(path))
                        try:
                            shutil.copytree(data_container, path)
                        except OSError:
                            shared.logger.console.debug('Could not copy patch to /public/patch')
                            pass
                    success_flag = True

    elif tarfile.is_tarfile(data_container):
        shared.logger.console.debug("Patch found in tar file")
        tarfid = tarfile.open(data_container)
        for member in tarfid:
            fname = member.name.split(os.path.sep)[-1]
            if set_naming_convention(fname, shared):
                fid = tarfid.extractfile(member)
                if lpt.is_rpm(fid, stream=True):
                    fid.close()
                    tarfid.extractall(path=extract_path)
                    # shared.id_rpm_contents = lpt.rpm2cpio(fid)
                    set_patchname(shared)
                    success_flag = True
                fid.close()
        tarfid.close()

    if not success_flag:
        shared.log(shared.ID_RPM_NOT_FOUND)
    return success_flag


def set_command_options(patch, dry_mode=False):
    shared.logger.console.debug("Setting Command Options")
    command = list([shared.name, shared.cmnd, '-l'])
    if dry_mode:
        command.append('-n')
    if shared.opts.verbose:
        command.append('-v')
    if shared.opts.nopatchscripts:
        command.append('-z')
    if shared.opts.force:
        command.append('-f')
    if shared.opts.last:
        command.append('-s')

    name, version, indx, promo = shared.name_version_indx
    msg = "set_command_options: {mode}: {nvi}".format(mode=shared.mode, nvi=shared.name_version_indx)
    shared.logger.console.debug(msg)

    if version is not None and len(version) > 0 and promo not in ('c', 'b'):
        patch_str = '-'.join([name, version])
    else:
        patch_str = name

    command.append(patch_str)
    shared.logger.console.debug(command)
    return command


def set_name_version_indx(shared):
    """Determine Patch Name and Version
    :param patch_name:
    :param patches: installed_patches instance
    :return tuple (name, version, index)
    """
    shared.logger.console.debug("Setting Name_Version_Indx")
    # Assume the timestamp consists of a pattern of at least 8 decimals
    name = version = patch_indx = promo = ''

    if 'new' in shared.naming_convention:
        id_rpm = shared.id_rpm.split('-')[0]
    else:
        id_rpm = shared.id_rpm

    installed_patch = [(x.name, x.version) for x in shared.installed_patches if id_rpm in '-'.join([x.name, x.version])]
    if installed_patch:
        patch_indx = shared.installed_patches.index(installed_patch[0][0])
        name = installed_patch[0][0]
        version = installed_patch[0][1]
    else:
        patch_indx = None
        if 'old' in shared.naming_convention:

            if re.search(r'(.+)-([0-9]{12})?', shared.id_rpm):
                pattern = r'(.+)-([0-9]{12})?'
                groups = 2
            else:
                pattern = r'(.+)'
                groups = 1

            match = re.match(pattern, shared.id_rpm)
            groups = match.groups()
            if len(match.groups()) > 1:
                name, version = match.groups()[::1]
            else:
                name = shared.id_rpm
                version = ''

        elif 'new' in shared.naming_convention:
            match = re.match(shared.conf.get('match', 'new_patches'),
                             shared.id_rpm)
            product, release, rc, patch_number, promo = match.groups()
            msg = "{mode}:PromotionLevel {promo}".format(mode=shared.mode,
                                                         promo=promo)
            shared.logger.console.debug(msg)
            msg = "{mode}:PatchName {id}".format(mode=shared.mode,
                                                 id=shared.id_rpm)
            shared.logger.console.debug(msg)
            if re.search(r'(.+)-(.+)(.noarch.rpm)', shared.id_rpm):
                pattern = r'(.+)-(.+)(.noarch.rpm)'
                groups = 3
            elif re.search(r'(.+)-(.+)', shared.id_rpm):
                pattern = r'(.+)-(.+)'
                groups = 2
            else:
                pattern = '(.+)'
                groups = 1

            vers_match = re.match(pattern, shared.id_rpm)

            if groups > 1:
                version = vers_match.groups()[1]
                name = vers_match.groups()[0]
            else:
                name = vers_match.groups()[0]
                version = ''

        else:
            shared.log(shared.INVALID_PATCH_NAME)

    shared.name_version_indx = (name, version, patch_indx, promo)


def check_system_is_running():
    """D000329773 Phase 2 (Validate System): Product is Running
    """
    if lpt.SystemFactory.get_system(shared.conf).is_running():
        shared.log(shared.SYSTEM_IS_RUNNING,
                   exit=1,
                   lpt_command=shared.cmnd)


def nodes_in_sync():
    """Check Sync Between Nodes
    :return bool: Nodes in sync flag
    """
    if shared.node_iteration_flag and shared.mngr:
        nodes_out_of_sync = lpt.check_sync(shared)
        if nodes_out_of_sync:
            if shared.opts.json:
                shared.result.update({"in_sync": False})
            else:
                shared.log(shared.NODES_OUT_OF_SYNC,
                           nodes=", ".join(nodes_out_of_sync))
            return False
        if not shared.opts.local and not shared.opts.json:
            shared.log(shared.NODES_IN_SYNC)
        elif shared.opts.local and shared.opts.json:
            shared.result.update({"in_sync": True})
    return True


def run_dry_mode(patch):
    """Dry run: Iterate over nodes
    :param <Patch> patch: patch instance
    """
    if not shared.opts.json:
        shared.log(shared.DRY_RUN,
                   fill_screen=True,
                   lpt_command=shared.cmnd)
    status, failed_nodes = lpt.iterate(set_command_options(patch, dry_mode=True), shared)

    # Commit: exit if any node in the iteration shared.failed in the dry run
    if not status:
        shared.log(shared.SYSTEM_FAILED_ON_NODE,
                   exit=True,
                   lpt_command=shared.cmnd,
                   nodes=" ".join(failed_nodes))
    else:
        # Dry run: finished!
        if shared.opts.dry:
            fail_stat = "succeeded" if status else "returned failure(s)"
            shared.log(shared.SYSTEM_DRY_RUN_STATE,
                       fill_screen=True,
                       exit=True,
                       lpt_command=shared.cmnd,
                       stat=fail_stat)
    shared.log(shared.SYS_COMMIT,
               fill_screen=True,
               lpt_command=shared.cmnd)

    if not status and not shared.opts.json:
        shared.log(shared.SYSTEM_FAILED_ON_NODE,
                   exit=True,
                   lpt_command=shared.cmnd,
                   nodes=shared.node.upper())


def last_messages_handler(patch):
    """Handle last messages
    :param <Patch> patch: patch instance"""

    if not shared.opts.dry:

        if shared.opts.local:
            if shared.fail:
                shared.log(shared.CMND_OF_PATCH_FAILED_ON_NODE,
                           file_log=True,
                           lpt_command=shared.cmnd.capitalize(),
                           patch_name=patch.name,
                           node=shared.conf.get("node", "type"))
            else:
                shared.log(shared.CMND_OF_PATCH_COMPLETED_ON_NODE,
                           fill_screen=True,
                           file_log=True,
                           lpt_command=shared.cmnd.capitalize(),
                           patch_name=patch.name,
                           node=shared.conf.get("node", "type"))
        else:
            if shared.fail:
                shared.log(shared.SYS_FAILED,
                           file_log=True,
                           exit=True,
                           lpt_command=shared.cmnd,
                           patch_name=patch.name)
            else:
                shared.log(shared.SYS_COMPLETED,
                           fill_screen=True,
                           file_log=True,
                           exit=True,
                           lpt_command=shared.cmnd,
                           patch_name=patch.name)


def run_on_spc(patch):
    """Check if patch contains SPC targets
    :param <Patch> patch: patch instance
    :param string pattern: search for servicepc
    :return bool: true if spc targets found
    """
    for item in patch.patch_content["patch_content"]:
        for node in item["node"]:
            if node.lower() in SPC_PATTERNS:
                return True
    return False


def spc_pure_patch(patch):
    """
    Return True if the given patch_content list shows a pure SPC patch.
    """
    # content = patch.patch_content["patch_content"]
    # return all(["servicepc" in map(str.lower, map(str, rpm["node"]))
    #             for rpm in content])
    return False


def install_or_backout():
    if not shared.opts.json:
        shared.log(shared.HOST_NODE,
                   fill_screen=True,
                   node=shared.node,
                   node_type=shared.conf.get("node", "type"))

    # D000329773 Phase 2 (Validate System): Product is Running (v15.0)
    if shared.systemOccupiedCheck:
        check_system_is_running()
    # A patch update operation (install, backout) is applied on the system via
    # the management node (normal case); all nodes need to have the same patch
    # state and view. The system needs to be healthy for a patch update
    # (ie install or backout) operation. Doing this also checks along whether
    # all configured nodes are reachable and responding. The other use case of
    # 'local' install is covered elsewhere.
    if shared.node_iteration_flag and not nodes_in_sync():
        return 1

    # D000329773 Phase 2 (Validate System): System Check, Patch RPMs
    # Moved to install.command_install_commit
    # (see http://boa-pit.asml.com:8080/browse/LPT-787)

    # Phase 2 - Check Patch
    if shared.cmnd == "install":
        from asml_patch.asml_patch_install import command_install_parse as parse
    else:
        from asml_patch.asml_patch_backout import command_backout_parse as parse

    if shared.cmnd == "backout":
        if len(shared.installed_patches) < 1:
            shared.log(shared.PATCH_NOT_INSTALLED,
                       exit=True)

        backout_patch = ""
        if not shared.args and shared.opts.last:
            backout_patch = shared.installed_patches[-1]
        else:
            for patch in shared.installed_patches:
                if patch.name in shared.args[0]:
                    backout_patch = patch

        if not backout_patch:
            shared.log(shared.PATCH_NOT_INSTALLED,
                       exit=True)

        if lpt.(shared.installed_patches, backout_patch.name):
            shared.log(shared.NOBACKOUTABLE,
                       exit=True,
                       patch_name=backout_patch.name,
                       patch_list=lpt.patch_required(shared.installed_patches,
                                                     backout_patch.name))
        else:
            if shared.opts.last:
                shared.id_rpm = backout_patch.name
            elif (len(shared.args) > 0):

                if backout_patch.name in shared.args[0]:
                    pattern = '([\d]{12}|[\d]{8}_[\d]{6})'
                    shared.id_rpm = backout_patch.name + '-' + backout_patch.version
                    if re.search(pattern, shared.args[0]):
                        if not backout_patch.version in shared.args[0]:
                            shared.log(shared.NO_PATCH_VERSION,
                                       exit=True)
                    else:
                        set_naming_convention(shared.id_rpm, shared)
                        set_patchname(shared)

                elif not validate_patch(shared.args[0]):
                    shared.log(shared.PATCH_NOT_INSTALLED,
                                exit=True)

    if shared.cmnd == 'install':
        if (len(shared.args) > 0) and not validate_patch(shared.args[0]):
            shared.log(shared.PATCH_NOT_FOUND_OR_INVALID,
                        exit=True)

        for patch in shared.installed_patches:
            pname = patch.name
            if 'new' in get_naming_convention(patch.name):
                pname = re.match(shared.conf.get('match', 'new_patches'), patch.name).group()[:-1]
                # if patch.name[-1] not in ('b', 'c',):
                #     patch.name = patch.name[:-1]
            if pname in shared.args[0]:
                if patch.version in shared.args[0]:
                    shared.log(shared.PATCH_ALREADY_INSTALLED,
                                exit=True)
                else:
                    shared.log(shared.DIFFERENT_PATCH_VERSION,
                                exit=True)

    # # !HERE
    if hasattr(shared, 'id_rpm'):
        set_naming_convention(shared.id_rpm, shared)
    else:
        set_naming_convention(shared.args[0], shared)
    msg = "{mode}: {id}".format(mode=shared.mode, id=shared.id_rpm)
    shared.logger.console.debug(msg)
    set_name_version_indx(shared)
    patch = parse(shared)
    # set if patch has rpms for SPC node
    shared.spc = spc_pure_patch(patch)

    if not patch:
        shared.log(shared.UNSUCCESSFUL_PATCH_INFO)
        return 1

    if not patch.patch_content:
        shared.log(shared.INCOMPLETE_PATCH)
        return 1

    # Be able to give the exact name and version to install and backout as
    # well as remote machines
    patch.id = "{name}-{vers}".format(name=patch.name, vers=patch.version)

    if shared.cmnd == "backout":
        if lpt.patch_required(shared.installed_patches, patch.name):
            shared.log(shared.NOBACKOUTABLE,
                       exit=True,
                       patch_name=patch.name,
                       patch_list=lpt.patch_required(shared.installed_patches,
                                                     patch.name))

    # If we're not in the dry run stage, save our log to file
    if not shared.opts.dry:
        shared.logger.patch_name = patch.name + '-' + patch.version
        shared.logger.flush_patch_log_to_file()

    if shared.cmnd in ("install",):
        # D000329773 Phase 2 (Validate System): Patch already installed
        from asml_patch.asml_patch_install import command_install_commit as commit

        # V.7 baselineCheck enabled
        # TODO make baseline check before dry-run phase
        if shared.baselineCheck and shared.opts.local:
            shared.pass_base = lpt.build_install_baseline(patch, shared)
            if not shared.pass_base and not shared.opts.force:
                return 1

        # V.8 overlap detection enabled
        if shared.overlapDetection and shared.opts.local:
            shared.pass_over = lpt.check_rpm_overlap(patch, shared)
            if not shared.pass_over and not shared.opts.force:
                return 1

    if shared.cmnd in ("backout",):
        # D000329773 Phase 2 (Validate System): Baseline Check (Backout)
        from asml_patch.asml_patch_backout import command_backout_commit as commit
        if shared.baselineCheck and shared.opts.local:
            lpt.check_backout_baseline(patch, shared)

    # Superfluous mode detection
    if (shared.baselineCheck or shared.overlapDetection) \
            and shared.opts.force and shared.opts.local:
        shared.sf_force = lpt.set_superfluous_force_flag(patch, shared)
    else:
        shared.sf_force = False

    # Assign commit function for either install or backout
    shared.commit = commit

    # D000329773 Phase 3 (Dry Run Patch): Patch script: pre-install --dry-run
    if shared.prePostScripts and shared.opts.local and shared.opts.dry:
        patch_scripts = lpt.PatchScripts(patch, shared)
        if patch_scripts.pre_action() != 0:
            return 1
        # Remove temporary files
        patch_scripts.cleanup()

    # D000329773 Phase 3 (Dry Run Patch): Yum RPMs Dry Run anyway
    if shared.node_iteration_flag:
        run_dry_mode(patch)

    if shared.node == shared.conf.get("system", "manager").lower():
        if shared.spc and shared.opts.local and shared.opts.dry:
            SPC_patch = lpt.SPCManager(shared,
                                       patch,
                                       shared.cmnd,
                                       pattern="servicepc")
            if shared.opts.dry:
                SPC_patch.dry_action(shared.cmnd)

    # D000329773 Phase 3 (Dry Run Patch): Patch script: pre-install --dry-run
    if shared.prePostScripts and not shared.opts.dry and shared.opts.local:
        patch_scripts = lpt.PatchScripts(patch, shared)
        if patch_scripts.pre_action() != 0:
            return 1

    ### D000329773 Phase 4 (Apply Patch): Yum RPMs Install/Backout
    if shared.node_iteration_flag and not shared.opts.dry:
        # Commit: Iterate over nodes
        success, failed_nodes = lpt.iterate(set_command_options(patch), shared)
        if not success:
            shared.log(shared.SYSTEM_FAILED_ON_NODE,
                        file_log=True,
                        lpt_command=shared.cmnd,
                        nodes=" ".join(failed_nodes))
            return 1

    if not shared.opts.dry and shared.opts.local:
        nds_cmd = " ".join([shared.name, shared.cmnd, "-l", patch.id])
        msg = """Running {0} on {1}""".format(nds_cmd, shared.conf.get('node', 'type'))
        shared.logger.system_file_logger.info(msg)

    if shared.opts.local:
        if not shared.commit(shared, patch):
            return 1

    if shared.node == shared.conf.get("system", "manager").lower():
        if shared.spc and shared.opts.local and not shared.opts.dry:
            SPC_patch = lpt.SPCManager(shared, patch, shared.cmnd, pattern="servicepc")
            SPC_patch.real_action(shared.cmnd)

    # Handle last messages
    if not shared.opts.dry:
        last_messages_handler(patch)

    # D000329773 Phase 4 (Apply Patch): Patch script: post-install
    if shared.prePostScripts and not shared.opts.dry and shared.opts.local:
        # If v.xx prePostScripts allowed, run post scripts and cleanup
        patch_scripts.post_action()
        patch_scripts.cleanup()

    # D000329773 Base_0130-0133/Over_0130-0133 (Forced mode) (Part 2/2)
    if shared.cmnd in ("install",) and shared.opts.force and shared.opts.local:
        lpt.update_patch_data(patch, shared)

    return 0


def set_installed_patches(shared):
    old_pattern = shared.conf.get("match", "patches")
    new_pattern = shared.conf.get("match", "new_patches")
    shared.installed_patches = []
    pattern = '({old}|{new})'.format(old=old_pattern, new=new_pattern)
    for rpm in shared.yb.searchTag(mode=2, pattern=pattern):
        shared.installed_patches.append(lpt.InstalledPatch(rpm,
                                                           conf=shared.conf))


def check_system_integrity():
    """Check if system configuration has been hampered with"""
    if not lpt.check_file_integrity(shared.FEATURE_CONFIG, ["MD5Checksum"]):
        shared.log(shared.LPT_SYS_CONFIG_CHANGED,
                   exit=True)


def check_patch_name(fname):
    """Check if patch name conforms to predefined pattern"""
    name = fname.split(os.sep)[-1]
    pattern = shared.conf.get('match', 'patches')
    if not re.match(pattern, name):
        shared.log(shared.PATCH_NOT_FOUND_OR_INVALID,
                   exit=True)


def main(argv=None):
    """
    Main application structure and sequence.
    :param list argv: List of asml_patch arguments
    :return: OS EXIT_FAILURE or EXIT_SUCCESS
    """
    # Set process execution mode for debug strings
    shared.mode = 'LOCAL' if shared.opts.local else 'GLOBAL'
    # Check Node Privileges
    if not shared.mngr and not shared.opts.local:
        shared.log(shared.SYS_CMD_NOT_ALLOWED_ON_NODE,
                   exit=True)
    # Require root rights for system-invasive commands
    if not shared.is_root:
        if shared.cmnd in ("install", "backout",):
            shared.log(shared.INVASIVE_MUST_BE_ROOT,
                       exit=True)

    shared.node_iteration_flag = (shared.mngr and
                                  not shared.opts.local)

    # TODO: CHECK BELOW patch extraction
    lpt.Patch.conf = shared.conf

    if not shared.mngr:
        def need_mngr(self):
            raise Exception("Patch needs to be extracted on management node")

        lpt.Patch.extract = need_mngr

    # Instantiate installed patches list
    if shared.cmnd not in ("release", "config",):
        set_installed_patches(shared)

    check_system_integrity()
    atexit.register(lpt.cleanup, shared.yb)

    if shared.cmnd in ("install", "backout",) and (not shared.opts.last):
        # Check for correct names prior all else
        # TODO: Remove Below comment if not needed
        # check_patch_name(shared.args[0])
        pass

    if shared.cmnd in ("backout",) and shared.opts.last and \
            not shared.installed_patches:
        shared.log(shared.NO_INSTALLED_PATCHES,
                   exit=True)

    # D000329773 Phase 1 (Validate Patch): Extract, Validate File/Content
    if shared.cmnd in ("install", "backout",):
        return install_or_backout()

    if shared.cmnd in ("list",):
        if shared.node_iteration_flag:
            str_list_cmnd = [shared.name, shared.cmnd, "-l"]
            str_list_cmnd.append("-j") if shared.opts.json else None
            str_list_cmnd.append("-c") if shared.opts.compact else None
            ret, failed_nodes = lpt.iterate(str_list_cmnd, shared)
            if failed_nodes:
                shared.log(shared.SYSTEM_FAILED_ON_NODE,
                           exit=True,
                           lpt_command=shared.cmnd,
                           nodes=", ".join(failed_nodes))
        if shared.opts.local:
            if not shared.opts.json:
                shared.log(shared.HOST_NODE,
                           fill_screen=True,
                           node=shared.node,
                           node_type=shared.conf.get("node", "type"))
            if not lpt.command_list(shared.opts, shared.installed_patches):
                shared.log(shared.LIST_COMMAND_ERR,
                           exit=True)

    if shared.cmnd in ("validate",):
        if shared.node_iteration_flag:
            str_validate_cmnd = [shared.name, shared.cmnd, "-l"]
            str_validate_cmnd.append("-j") if shared.opts.json else None
            str_validate_cmnd.append("-s") if shared.opts.sync else None
            str_validate_cmnd.append("-p") if shared.opts.patches else None
            ret, failed_nodes = lpt.iterate(str_validate_cmnd, shared)
            if failed_nodes:
                shared.log(shared.SYSTEM_FAILED_ON_NODE,
                           lpt_command=shared.cmnd,
                           nodes=", ".join(failed_nodes))
        if shared.opts.local:
            if not shared.opts.json:
                shared.log(shared.HOST_NODE,
                           fill_screen=True,
                           node=shared.node,
                           node_type=shared.conf.get("node", "type"))
            res = lpt.command_validate(shared)
            if not shared.opts.json:
                if shared.mngr:
                    if not (shared.opts.patches and not shared.opts.sync):
                        result = "Succeeded" if res else "Failed"
                        shared.log(shared.SYS_VALIDATION_STATE,
                                   fill_screen=True,
                                   result=result)
            else:
                shared.logger.console.info(json.dumps(shared.result))

    if shared.cmnd in ("config",):
        if not lpt.command_config(shared.conf, shared.opts):
            sys.exit(1)

    if shared.cmnd in ("info",):
        set_naming_convention(shared.args[-1], shared)
        if not validate_patch(shared.args[-1]):
            shared.log(shared.PATCH_NOT_FOUND_OR_INVALID,
                       exit=True)
        if not lpt.command_info(shared):
            sys.exit(1)

    if shared.cmnd in ("release",):
        str_release_cmnd = [shared.name, shared.cmnd]
        str_release_cmnd.append("-j") if shared.opts.json else None

        if shared.node_iteration_flag:
            str_release_cmnd.append("-l")
            ret, failed_nodes = lpt.iterate(str_release_cmnd, shared)

        if shared.opts.local:
            if not shared.opts.json:
                shared.log(shared.HOST_NODE,
                           new_line=True,
                           node=shared.node,
                           node_type=shared.conf.get("node", "type"))
            release_data = shared.release.format(shared.opts)
            shared.logger.console.info(release_data)


if __name__ == '__main__':
    # Instantiate Shared Data Container
    shared = lpt.ASMLPatchNode(sys.argv, date=__date__, version=__version__)
    sys.exit(main(argv=sys.argv))
