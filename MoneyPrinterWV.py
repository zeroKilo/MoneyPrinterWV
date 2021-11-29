# coding=<cp1252>
import ContractChecker
import Helper
import TokenScanner
import TokenWatcher
from web3 import Web3
from colorama import init, Back, Fore, Style
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
Helper.showSplash()
client = Web3(Web3.HTTPProvider(my_provider))
client.middleware_onion.inject(geth_poa_middleware, layer=0)
Helper.init(client)
TokenScanner.init()
ContractChecker.init(options['bsc_api_key'])
TokenWatcher.init()
while True:
    newTokenAddress = TokenScanner.findNewToken(client, save_interval, fresh_max, amount_threshold, dump_contracts)
    check = ContractChecker.checkContract(client, newTokenAddress, 0, False, True)
    if check[0]:
        details = ContractChecker.getDetails(check[1])
        ContractChecker.showDetails(check[1])
        tx_result = ContractChecker.checkRecentTX(newTokenAddress, recent_tx_max)
        if tx_result[0]:
            print(Helper.timestamp(), Fore.GREEN + Helper.checkMark() + " Recent TX Count =", tx_result[1], Style.RESET_ALL)
        else:
            print(Helper.timestamp(), Fore.YELLOW + "X Recent TX Count =", tx_result[1], Style.RESET_ALL)
        if tx_result[2]:
            print(Helper.timestamp(), Fore.GREEN + Helper.checkMark() + " Found contract creation", Style.RESET_ALL)
        else:
            print(Helper.timestamp(), Fore.RED + "X Contract creation not found", Style.RESET_ALL)
        valid = ContractChecker.getValidated(newTokenAddress)
        if valid[0] and len(details[1]) == 0 and tx_result[2]:
            print(Helper.timestamp(), Fore.GREEN + Helper.checkMark() + " Is BSCScan verified", Style.RESET_ALL)
            if open_tabs:
                Helper.openBrowserTabs(newTokenAddress)
            if play_sound:
                Helper.playKaChing()
            result = ContractChecker.getTotalSupply(newTokenAddress)
            total_supply = 0
            if result[0]:
                total_supply = int(result[1])
                if total_supply > 0:
                    print(Helper.timestamp(), Fore.GREEN + Helper.checkMark() + " Total supply =", total_supply, Style.RESET_ALL)
                else:
                    print(Helper.timestamp(), Fore.RED + "X Total supply =", total_supply, Style.RESET_ALL)
            else:
                print(Helper.timestamp(), Fore.RED + "X Could not retrieve total supply!", Style.RESET_ALL)
            result = TokenWatcher.watch(client, newTokenAddress)
        else:
            print(Helper.timestamp(), Fore.RED + "X Is not BSCScan verified! ->", valid[1], valid[2], Style.RESET_ALL)
    else:
        print(Helper.timestamp(), Back.RED + Fore.BLACK + "ERROR PROCESSING CONTRACT!" + Style.RESET_ALL)


