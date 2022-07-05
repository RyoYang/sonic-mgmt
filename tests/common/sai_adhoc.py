"""
    Run 'commands' Ansible customized ad-hoc command implemented under ansible/library
    param: 
        host: either DUT hostname or PTF hostname
        inv_file : inventory
        cmd : customized command"
"""
def run_command(host, inv_file, cmd):
    results = []
    try:
        ansible_cmd = 'ansible -m shell -i ./ansible/{} {} -o -a'.format(inv_file, host)
        raw_output = get_raw_output(ansible_cmd, cmd)
        output_fields = raw_output.split('(stdout)', 1)[-1].strip()
        output_fields = output_fields.split('\n', 1)[0]
        print(output_fields)
        results = output_fields
    except Exception as e:
        logger.error('Failed to run commands, exception: {}'.format(repr(e)))

    logger.info(results)
    return results


"""
    Run 'copy' Ansible ad-hoc command
    param: 
        host: either DUT hostname or PTF hostname
        inv_file : inventory
        cmd : must in format of "src=<path> dest=<path>"
"""
def run_copy(host, inv_file, cmd):
    try:
        ansible_cmd = 'ansible -m copy -i ./ansible/{} {} -o -a'.format(inv_file, host)
        raw_output = get_raw_output(ansible_cmd, cmd)

        output_fields = ""
        if 'CHANGED =>' in raw_output:
            output_fields = raw_output.split('CHANGED =>', 1)
        elif 'SUCCESS =>' in raw_output:
            output_fields = raw_output.split('SUCCESS =>', 1)
        else:
            raise Exception("Failed copying file")

        file_dest = json.loads(output_fields[1].strip())["dest"]
        logger.info("Copying to {}".format(file_dest))
    except Exception as e:
        logger.error('Failed to run commands, exception: {}'.format(repr(e)))


"""
    Run 'fetch' Ansible ad-hoc command
    param: 
        host: either DUT hostname or PTF hostname
        inv_file : inventory
        cmd : must in format of "src=<path> dest=<path> flat=<true or false>"
"""
def run_fetch(host, inv_file, cmd):
    try:
        ansible_cmd = 'ansible -m fetch -i ./ansible/{} {} -o -a'.format(inv_file, host)
        raw_output = get_raw_output(ansible_cmd, cmd)

        output_fields = ""
        if 'CHANGED =>' in raw_output:
            output_fields = raw_output.split('CHANGED =>', 1)
        else:
            raise Exception("Failed copying file")

        file_dest = json.loads(output_fields[1].strip())["dest"]
        logger.info("Fetching file to {}".format(file_dest))
    except Exception as e:
        logger.error('Failed to run commands, exception: {}'.format(repr(e)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""
        Taking different parameters for running commands on either DUT or PTF during SAI testing.
        """
    )

    parser.add_argument("--type", type=str, dest="host_type", choices=["dut", "ptf"], help="host type", required=True)
    parser.add_argument("-t", dest="exe_type", type=str, choices=["cmd", "copy", "fetch"], help="execution type", required=True)
    parser.add_argument("-n", dest="host_name", type=str, help="host name", required=True)
    parser.add_argument("-c", dest="commands", type=str, help="commands")

    args = parser.parse_args()
    
    dut, ptf, inv_name = get_info_helper(args.host_name)

    if args.host_type =='dut':
        host = dut
    elif args.host_type =='ptf':
        host = ptf

    if args.exe_type == "cmd":
        run_command(host, inv_name, args.commands)
    elif args.exe_type == "copy":
        run_copy(host, inv_name, args.commands)
    elif args.exe_type == "fetch":
        run_fetch(host, inv_name, args.commands)
    else:
        pass
