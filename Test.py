# coding=<cp1252>
import ContractChecker
import Helper
import TokenScanner
import TokenWatcher
from web3 import Web3
from colorama import init, Fore, Back, Style
from web3.middleware import geth_poa_middleware


my_provider = "https://bsc-dataseed4.defibit.io"


init()
options = Helper.loadOptions()
play_sound = options['play_sound'] == 1
open_tabs = options['open_tabs'] == 1
fresh_max = options['fresh_max']
save_interval = options['save_interval']
amount_threshold = options['threshold']
dump_contracts = options['dump_contracts'] == 1
recent_tx_max = options['recent_tx_max']
client = Web3(Web3.HTTPProvider(my_provider))
client.middleware_onion.inject(geth_poa_middleware, layer=0)
Helper.init(client)
TokenScanner.init()
ContractChecker.init(options['bsc_api_key'])
TokenWatcher.init()
address = client.toChecksumAddress('0xFfbBbA54125b6574d20A4A4B5ee2cfe4dfA5499e')
check = ContractChecker.checkContract(client, address)
if check[0]:
    ContractChecker.showDetails(check[1], True)
    tx_result = ContractChecker.checkRecentTX(address, recent_tx_max, True)
    if tx_result[0]:
        print(Helper.timestamp(), Fore.GREEN + Helper.checkMark() + " Recent TX Count =", tx_result[1], Style.RESET_ALL)
    else:
        print(Helper.timestamp(), Fore.YELLOW + "X Recent TX Count =", tx_result[1], Style.RESET_ALL)
    if tx_result[2]:
        print(Helper.timestamp(), Fore.GREEN + Helper.checkMark() + " Found contract creation", Style.RESET_ALL)
    else:
        print(Helper.timestamp(), Fore.RED + "X Contract creation not found", Style.RESET_ALL)
    valid = ContractChecker.getValidated(address)
    if valid[0]:
        print(Helper.timestamp(), Fore.GREEN + Helper.checkMark() + " Is BSCScan verified", Style.RESET_ALL)
    else:
        print(Helper.timestamp(), Fore.RED + "X Is not BSCScan verified! ->", valid[1], valid[2], Style.RESET_ALL)
    result = ContractChecker.getTotalSupply(address)
    total_supply = 0
    if result[0]:
        total_supply = int(result[1])
        if total_supply > 0:
            print(Helper.timestamp(), Fore.GREEN + Helper.checkMark() + " Total supply =", total_supply, Style.RESET_ALL)
        else:
            print(Helper.timestamp(), Fore.RED + "X Total supply =", total_supply, Style.RESET_ALL)
    else:
        print(Helper.timestamp(), Fore.RED + "X Could not retrieve total supply!", Style.RESET_ALL)
    result = TokenWatcher.watch(client, address)
