import os.path
import json
import collections
import urllib.request
import Helper
from os import path
from pyevmasm import disassemble_all
from colorama import Fore, Back, Style


func_dic = {}
global_data = {}
func_dic_path = 'data\\func_list.txt'
bad_word_path = 'data\\bad_words.txt'


def init(bsc_api_key):
    global_data['apikey'] = bsc_api_key
    print(Helper.timestamp(), "Loading Function Dictionary...")
    func_dic.clear()
    with open(func_dic_path) as json_file:
        dic = json.load(json_file)
    func_dic.update(dic)
    print(Helper.timestamp(), "Loading Bad Word List...")
    with open(bad_word_path) as file:
        global_data['badWords'] = file.read().splitlines()


def getValidated(address):
    url = "https://api.bscscan.com/api?module=contract&action=getabi&address=" + address + "&apikey=" + global_data['apikey']
    data = urllib.request.urlopen(url).read()
    output = json.loads(data)
    return output['status'] == '1', output['message'], output['result']


def isContract(client, address):
    code = client.eth.getCode(address)
    return len(code) > 0


def getTotalSupply(address):
    url = "https://api.bscscan.com/api?module=stats&action=tokensupply&contractaddress=" + address + "&apikey=" + global_data['apikey']
    data = urllib.request.urlopen(url).read()
    output = json.loads(data)
    return output['status'] == '1', output['result']


def getRecentTX(address, count=10):
    url = 'https://api.bscscan.com/api?module=account&action=txlist&address=' + address + \
          '&startblock=0&endblock=99999999&page=1&offset=' + str(count) + '&sort=desc&apikey=' + global_data['apikey']
    data = urllib.request.urlopen(url).read()
    return json.loads(data)['result']


def getRecentEvents(address):
    url = 'https://api.bscscan.com/api?module=logs&action=getLogs&' +\
          'fromBlock=0&toBlock=99999999' + \
          '&address=' + address + '&apikey=' + global_data['apikey']
    data = urllib.request.urlopen(url).read()
    return json.loads(data)['result']


def getRecentTXCount(address, show_tx=False):
    result = getRecentTX(address, 100)
    index = 0
    found_creation = False
    for tx in result:
        if len(tx['input']) > 4 and tx['contractAddress'] == "":
            func_hash = tx['input'][2:10]
            if show_tx:
                print(Helper.timestamp(), "%02d" % index, func_dic[func_hash.upper()])
            index = index + 1
        if len(tx['input']) > 4 and tx['contractAddress'] != "":
            if show_tx:
                print(Helper.timestamp(), "%02d" % index, ">>>Contract creation<<<")
            index = index + 1
            found_creation = True
    return len(result), found_creation


def getFuncName(address, func_hash):
    if len(func_hash) != 8:
        return "<Invalid hash>"
    if func_hash == '60806040':
        return "<Contract creation>"
    if func_hash in func_dic:
        return func_dic[func_hash]
    url = "https://www.4byte.directory/api/v1/signatures/?hex_signature=0x" + func_hash
    data = urllib.request.urlopen(url).read()
    output = json.loads(data)
    entry = ""
    for result in output['results']:
        entry = entry + result['text_signature'] + " "
    if entry == "":
        entry = "###Unknown###, seen in %s" % address
    func_dic[func_hash] = entry
    sorted_dic = sorted(func_dic.items(), key=lambda x: x[1])
    dic = collections.OrderedDict(sorted_dic)
    with open(func_dic_path, 'w') as file:
        file.write(json.dumps(dic, indent=4))
    return entry


def checkRecentTX(address, threshold, show_tx=False):
    result = getRecentTXCount(address, show_tx)
    count = result[0]
    if count < threshold:
        return True, result[0], result[1]
    else:
        return False, result[0], result[1]


def makeTabs(tabs):
    result = ""
    for i in range(tabs):
        result = result + " "
    return result


def dumpOpcodes(opcodes, address, tabs):
    tt = makeTabs(tabs)
    if not path.exists('contracts'):
        os.mkdir('contracts')
    output = "contracts\\" + address + ".txt"
    if path.exists(output):
        return
    with open(output, 'w') as file:
        pc = 0
        for opc in opcodes:
            file.write("%08X %s\n" % (pc, opc))
            pc = pc + opc.size
    print(Helper.timestamp(), tt + "Dumped...")


def matchFunctions(client, address, opcodes, tabs=0, dump=False):
    tt = makeTabs(tabs)
    func_list = {}
    new_found_count = 0
    for i in range(len(opcodes)):
        if i < len(opcodes) - 4:
            op1 = opcodes[i]
            op2 = opcodes[i + 1]
            op3 = opcodes[i + 2]
            op4 = opcodes[i + 3]
            if op1.name == "PUSH4" and \
                    op2.name == "EQ" and \
                    op3.name == "PUSH2" and \
                    op4.name == "JUMPI":
                func_hash = '%08X' % op1.operand
                if not func_hash in func_dic:
                    new_found_count = new_found_count + 1
                    print(Helper.timestamp(), tt + Fore.GREEN + "Found new hash = %s %s" %
                          (func_hash, getFuncName(address, func_hash)), Style.RESET_ALL)
                func_list[func_hash] = func_dic[func_hash]
            if op1.name == "RETURNDATASIZE" and \
                    op2.name == "PUSH20" and \
                    op3.name == "GAS" and \
                    op4.name == "DELEGATECALL":
                print(Helper.timestamp(), tt + "Found delegate contract 0x%X" % op2.operand)
                checkContract(client, client.toChecksumAddress(op2.operand), tabs + 1, dump)
    return func_list, new_found_count


def quickCheckFuncName(name):
    n = name.lower()
    for w in global_data['badWords']:
        if w in n:
            return False
    return True


def showDetails(func_list, show_listing=False):
    details = getDetails(func_list)
    warnings = details[0]
    unknown = details[1]
    if show_listing:
        print(details[2])
    displayWarningsAndUnknown(warnings, unknown)


def getDetails(func_list):
    sorted_dic = sorted(func_list.items(), key=lambda x: x[1])
    func_listing = ""
    unknown = []
    warnings = []
    for f in sorted_dic:
        if f[1].startswith('###Unknown###'):
            unknown.append(f[0])
        else:
            if quickCheckFuncName(f[1]):
                func_listing = func_listing + str(Helper.timestamp()) + " -> " + f[1] + "\n"
            else:
                func_listing = func_listing + Fore.YELLOW + str(Helper.timestamp()) + "!-> " + f[1] + Style.RESET_ALL + "\n"
                warnings.append(f[1])
    func_listing = func_listing.strip()
    return warnings, unknown, func_listing


def displayWarningsAndUnknown(warnings, unknown):
    unknown_found = ""
    break_count = 0
    for u in unknown:
        unknown_found = unknown_found + u + " "
        break_count = break_count + 1
        if break_count == 8:
            unknown_found = unknown_found + "\n"
            break_count = 0
    if len(warnings) > 0:
        print(Helper.timestamp(), Fore.YELLOW + "X Found", len(warnings), "warnings!", Style.RESET_ALL)
        for w in warnings:
            print(Helper.timestamp(), Fore.YELLOW + "!->", w, Style.RESET_ALL)
    else:
        print(Helper.timestamp(), Fore.GREEN + Helper.checkMark() + " Found no warnings", Style.RESET_ALL)
    if len(unknown) > 0:
        print(Helper.timestamp(), Fore.RED + "X Found", len(unknown), "unknown functions [\n", unknown_found + "]", Style.RESET_ALL)
    else:
        print(Helper.timestamp(), Fore.GREEN + Helper.checkMark() + " Found no unknown functions", Style.RESET_ALL)


def checkContract(client, address, tabs=0, dump=False, quite=False):
    try:
        tt = makeTabs(tabs)
        print(Helper.timestamp(), tt + "Checking Contract...")
        bytecode = client.eth.getCode(address)
        opcodes = list(disassemble_all(bytecode))
        if dump:
            dumpOpcodes(opcodes, address, tabs)
        func_scan = matchFunctions(client, address, opcodes, tabs, dump)
        func_list = func_scan[0]
        new_found_count = func_scan[1]
        if not quite:
            print(Helper.timestamp(), tt + "Found", len(func_list), "functions,", new_found_count, "new")
        return True, func_list
    except Exception as e:
        print(Helper.timestamp(), Back.RED + Fore.BLACK + "Caught ERROR on contract scanning!" + Style.RESET_ALL)
        print(e)
        return False, e
