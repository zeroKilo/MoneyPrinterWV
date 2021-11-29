import Helper
import keyboard
import ContractChecker
from colorama import Fore, Back, Style

topic_dic = {
    '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef': 'Transfer',
    '0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925': 'Approval',
    '0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0': 'OwnershipTransferred'
}


def init():
    print(Helper.timestamp(), "Initializing watcher...")


def getEventType(topic):
    if topic in topic_dic:
        return topic_dic[topic]
    return "Unknown type " + topic


def getFuncNameFromInput(address, input_data):
    func_name = "<???>"
    if len(input_data) > 10:
        func_name = ContractChecker.getFuncName(address, input_data[2:10])
        if func_name.startswith('###Unknown###'):
            func_name = "<Unknown 0x" + input_data[2:10] + ">"
        else:
            func_name = "<" + func_name.split('(')[0] + ">"
    if 'ETHForTokens' in func_name:
        func_name = Back.LIGHTGREEN_EX + Fore.BLACK + "BUY" + Style.RESET_ALL
    if 'TokensForETH' in func_name:
        func_name = Back.RED + Fore.BLACK + "SELL" + Style.RESET_ALL
    if 'TokensForTokens' in func_name:
        if func_name == '<swapExactTokensForTokens>':
            func_name = inspectSwap(address, input_data, 330)
        elif func_name == '<swapExactTokensForTokensSupportingFeeOnTransferTokens>':
            func_name = inspectSwap(address, input_data, 330)
        else:
            func_name = Back.YELLOW + Fore.BLACK + "SWAP" + Style.RESET_ALL
    return func_name


def inspectSwap(address, data, start):
    pattern = address[2:].lower()
    count = int(data[start:start+64], 16)
    index = -1
    for i in range(0, count):
        pos = i * 64 + start + 64
        sub = data[pos:pos + 64]
        if pattern in sub.lower():
            index = i
    if index > 0:
        return Back.LIGHTGREEN_EX + Fore.BLACK + "BUY" + Style.RESET_ALL
    elif index == 0:
        return Back.RED + Fore.BLACK + "SELL" + Style.RESET_ALL
    else:
        return Back.YELLOW + Fore.BLACK + "SWAP" + Style.RESET_ALL


def printEvent(client, address, ev):
    ev_type = getEventType(ev['topics'][0])
    try:
        amount = 0
        if len(ev['data']) > 2:
            amount = int(ev['data'][2:], 16)
        details = client.eth.getTransaction(ev['transactionHash'])
        func_name = getFuncNameFromInput(address, details['input'])
        print(Helper.timestamp(),
              "Found TX " + ev['transactionHash'],
              ev_type, func_name,
              "Amount =", amount)
    except:
        return False
    return True


def processEvents(client, address, seen_tx, events):
    for i in range(0, len(events) - 1):
        if events[i]['timeStamp'] > events[i + 1]['timeStamp']:
            tmp = events[i]
            events[i] = events[i + 1]
            events[i + 1] = tmp
    for ev in events:
        hash_ev = ev['transactionHash']
        if hash_ev not in seen_tx:
            if printEvent(client, address, ev):
                seen_tx.append(hash_ev)


def watch(client, address):
    pattern = address[2:34].lower()
    print(Helper.timestamp(), Back.LIGHTGREEN_EX + Fore.BLACK + "Watching", address, "...", Style.RESET_ALL)
    result = ContractChecker.getValidated(address)
    if not result[0]:
        return False, "Contract not validated"
    seen_tx = []
    last_block = 0
    events = ContractChecker.getRecentEvents(address)
    processEvents(client, address, seen_tx, events)
    while True:
        if keyboard.is_pressed("x"):
            print()
            return False, "User aborted"
        block = client.eth.getBlock('pending', full_transactions=True)
        if block.number != last_block:
            last_block = block.number
            for tx in block['transactions']:
                found = False
                if tx['to'] and pattern in tx['to'].lower():
                    found = True
                if not found and tx['from'] and pattern in tx['from'].lower():
                    found = True
                if not found and tx['input'] and pattern in tx['input'].lower():
                    found = True
                if found:
                    if tx['hash'].hex() not in seen_tx:
                        seen_tx.append(tx['hash'].hex())
                        func_name = getFuncNameFromInput(address, tx['input'])
                        print(Helper.timestamp(), "Found pending TX", tx['hash'].hex(), func_name)
        events = ContractChecker.getRecentEvents(address)
        processEvents(client, address, seen_tx, events)
    return True, 'ok'
