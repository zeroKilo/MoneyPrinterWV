import json
import collections
import ContractChecker
import Helper
from time import time, sleep
from web3 import Web3
from colorama import Fore, Style


global_data = {}
token_list_path = 'data\\token_list.txt'


def init():
    global_data['save_block'] = 0
    print(Helper.timestamp(), "Loading Token Dictionary...")
    with open(token_list_path) as json_file:
        global_data['token_dic'] = json.load(json_file)


def findNewToken(client, save_interval, fresh_max, amount_threshold, dump_contracts):
    last_saved = time()
    save_block = 0
    print(Helper.timestamp(), "Scanning for new token...")
    while True:
        if (time() - last_saved) > save_interval:
            print(Helper.timestamp(), Fore.RED + "Saving..." + Style.RESET_ALL)
            sorted_dic = sorted(global_data['token_dic'].items(), key=lambda x: x[1])
            global_data['token_dic'] = collections.OrderedDict(sorted_dic)
            with open(token_list_path, 'w') as file:
                file.write(json.dumps(global_data['token_dic'], indent=4))
            last_saved = time()
        sleep(1)
        pending_block = client.eth.getBlock('pending', full_transactions=True)
        block = pending_block['number']
        if save_block != block:
            save_block = block
            pending_transactions = pending_block['transactions']
            for pending in pending_transactions:
                input_bytes = pending['input']
                try:
                    decoded = Helper.decodeContract(input_bytes)
                    if str(decoded[0]).startswith('<Function addLiquidityETH'):
                        print(Helper.timestamp())
                        token = decoded[1]['token']
                        amount = decoded[1]['amountETHMin']
                        amount = client.fromWei(amount, 'Ether')
                        amount = float(amount) * Helper.getETHPrice()
                        price = '[UNAVAILABLE]'
                        try:
                            price = Helper.calcSell(client, token, global_data['contract'])
                        except:
                            pass
                        if token in global_data['token_dic']:
                            global_data['token_dic'][token] = global_data['token_dic'][token] + 1
                            count = global_data['token_dic'][token]
                            color = Fore.BLUE
                            if count < fresh_max:
                                color = Fore.LIGHTYELLOW_EX
                            print(Helper.timestamp(), color + "Token seen again =", token, Style.RESET_ALL)
                            print(Helper.timestamp(), color + "Amount =", amount, "$", Style.RESET_ALL)
                            print(Helper.timestamp(), color + "Count =", global_data['token_dic'][token], Style.RESET_ALL)
                            print(Helper.timestamp(), color + "Price =", price, "$", Style.RESET_ALL)
                            ContractChecker.checkContract(client, client.toChecksumAddress(token), 0, dump_contracts)
                        else:
                            global_data['token_dic'][token] = 0
                            print(Helper.timestamp(), Fore.LIGHTGREEN_EX + "Found new token =", token, Style.RESET_ALL)
                            print(Helper.timestamp(), Fore.LIGHTGREEN_EX + "Amount =", amount, "$", Style.RESET_ALL)
                            print(Helper.timestamp(), Fore.LIGHTGREEN_EX + "Price =", price, "$", Style.RESET_ALL)
                            ContractChecker.checkContract(client, client.toChecksumAddress(token), 0, dump_contracts)
                            if price == '[UNAVAILABLE]' and amount >= amount_threshold:
                                return token
                except:
                    pass