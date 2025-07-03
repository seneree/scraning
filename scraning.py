import os
import re
import sys
import json
import time
import requests
from web3 import Web3
from eth_account import Account
from tronpy import Tron
from tronpy.keys import PrivateKey as TronPrivateKey
from mnemonic import Mnemonic
from bip44 import Wallet
from decimal import Decimal # Import Decimal module
import warnings
warnings.filterwarnings("ignore")

# Aktifkan fitur HD Wallet tanpa audit untuk eth_account.
Account.enable_unaudited_hdwallet_features()

# --- Konfigurasi File ---
PHRASE_FILE = "phrases.txt"  # File input berisi mnemonic
PRIVATEKEY_EVM_FILE = "privatekeyevm.txt"  # File output untuk private key EVM yang digenerate
PRIVATEKEY_TRON_FILE = "privatekeytron.txt"  # File output untuk private key TRON yang digenerate
INVALID_MNEMONIC_FILE = "invalid_mnemonics.txt"  # File output untuk mnemonic/key yang tidak valid
EVM_OUTPUT_FILE_PREFIX = "wallet_berisi_"  # Prefix file output untuk wallet EVM dengan saldo
TRON_OUTPUT_FILE = "wallet_berisi_stablecoin_tron.txt" # File output untuk wallet TRON dengan saldo

# Kunci API Anda (PASTIKAN INI SAMA PERSIS DENGAN YANG DI TRONGRID)
COVALENT_API_KEY = "" # <--- GANTI INI DENGAN KUNCI API ANDA YANG VALID
TRONGRID_API_KEY = "" # <--- GANTI INI DENGAN KUNCI API ANDA YANG VALID

# Setel kunci API Trongrid sebagai variabel lingkungan untuk tronpy
os.environ['TRONGRID_API_KEY'] = TRONGRID_API_KEY

# --- Konfigurasi Jaringan EVM dan RPC ---
EVM_NETWORKS = {
    "ethereum": "https://eth-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW",
    "bsc": "https://bnb-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW",
    "polygon": "https://polygon-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW",
    "arbitrum": "https://arb-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW",
    "optimism": "https://opt-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW",
    "avalanche": "https://avax-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW",
    "base": "https://base-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW" 
}

# Mapping nama jaringan ke Chain ID Covalent (diperlukan untuk Covalent API, jika ingin menambahkan scan semua token)
COVALENT_CHAIN_IDS = {
    "ethereum": "1",
    "bsc": "56",
    "polygon": "137",
    "arbitrum": "42161",
    "optimism": "10",
    "avalanche": "43114",
    "base": "8453"
}

# --- Block Explorer URLs untuk transaksi ---
# Format: { 'nama_jaringan': 'URL_dasar_transaksi' }
BLOCK_EXPLORER_URLS = {
    "ethereum": "https://etherscan.io/tx/",
    "bsc": "https://bscscan.com/tx/",
    "polygon": "https://polygonscan.com/tx/",
    "arbitrum": "https://arbiscan.io/tx/",
    "optimism": "https://optimistic.etherscan.io/tx/",
    "avalanche": "https://snowtrace.io/tx/",
    "base": "https://basescan.org/tx/",
    "tron": "https://tronscan.org/#/transaction/" # Tambahkan URL Tronscan
}

# ABI standar untuk fungsi ERC20 (name, decimals, balanceOf, dan transfer).
ERC20_ABI = json.loads("""
[
    {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}
]
""")

# EVM_STABLECOIN_CONTRACTS ini sekarang hanya digunakan untuk scan (Menu 1, untuk stablecoin yang sudah dikenal),
# bukan lagi sebagai satu-satunya sumber untuk pengiriman di Menu 2.
EVM_STABLECOIN_CONTRACTS = {
    "ethereum": {
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    },
    "bsc": {
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "USDC": "0x8AC76a51Cc950Ece8052dAE756f6087dCa39c57B",
        "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
    },
    "polygon": {
        "USDT": "0xc2132D05D31c914a87C66119Cfae09B4594C0333",
        "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9214f86397D"
    },
    "arbitrum": {
        "USDT": "0xFd086bc7Ab296b2Cc88566fA360ca2a69Df7607F",
        "USDC": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
        "MLK": "0x374c5fb7979d5fdbaad2d95409e235e5cbdfd43c" 
    },
    "optimism": {
        "USDT": "0x94b008aA295cde2698c92bE5FEf920fE557a802F",
        "USDC": "0x7F5c764cBc14f9669B88837Dc21913Bc9eEc88fE"
    },
    "avalanche": {
        "USDT": "0x9702230A8Fc983E856Ddb6aFb6Fcb606fE0C2A52",
        "USDC": "0xB97EF9Ef8734C71904dC67f15Fb5Fbb611F45Db"
    },
    "base": {
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 
        "USDbC": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA"
    }
}

# Alamat kontrak stablecoin TRON umum (TRC20).
TRON_STABLECOIN_CONTRACTS = {
    "USDT": "TR7NHqjeKQxGTCi8q8ZiFcpLzarXgByKE9", # USDT TRC20
    "USDJ": "TCFLL5nyC0LXxSvrp1E4V126K6FmP1Tchx", # USDJ TRC20
    "TUSD": "TUpMhErZL4d8Pyb229UoCHcZzgsfG1r2p1" # TUSD TRC20
}

# --- Fungsi Utilitas ---

def is_valid_mnemonic_length(words):
    return len(words) in [12, 15, 18, 21, 24]

def write_to_file(filename, content):
    mode = 'a' if os.path.exists(filename) else 'w'
    with open(filename, mode) as f:
        f.write(content + "\n")

def load_and_clean_phrases(file_path=PHRASE_FILE, show_detail=False):
    try:
        with open(file_path, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' tidak ditemukan. Pastikan ada.")
        return []
    except Exception as e:
        print(f"❌ Error: Gagal membaca file '{file_path}': {e}")
        return []

    cleaned_mnemonics = []
    invalid_mnemonics_buffer = []

    if show_detail:
        print(f"\n--- Memulai validasi mnemonic dari '{file_path}' ---")
    for line_num, line in enumerate(lines, 1):
        original_line = line 
        
        if ':' in line:
            line = line.split(":", 1)[1].strip()
        
        words = line.split()

        if not words: 
            continue

        try:
            if not is_valid_mnemonic_length(words):
                raise ValueError(f"Panjang mnemonic tidak valid ({len(words)} kata).")

            mnemo = Mnemonic("english")
            if not mnemo.check(line):
                raise ValueError("Checksum mnemonic tidak valid.")
            
            cleaned_mnemonics.append(line)
            if show_detail:
                print(f"✅ Baris {line_num}: Mnemonic valid ({len(words)} kata): {line[:50]}...")
        except Exception as e:
            error_message = f"Baris {line_num}: '{original_line}' -> Error: {e}"
            invalid_mnemonics_buffer.append(error_message)
            if show_detail:
                print(f"⚠️ Baris {line_num}: Mnemonic tidak valid: '{original_line[:50]}...' -> {e}")
    
    if invalid_mnemonics_buffer:
        print(f"\n--- Ditemukan {len(invalid_mnemonics_buffer)} mnemonic tidak valid. ---")
        print(f"Detail mnemonic yang tidak valid disimpan ke '{INVALID_MNEMONIC_FILE}'")
        for inv_mnemonic in invalid_mnemonics_buffer:
            write_to_file(INVALID_MNEMONIC_FILE, inv_mnemonic)
        if show_detail:
            print("-" * 40)
    elif show_detail:
        print("\n🎉 Semua mnemonic di file valid!")

    if show_detail:
        print(f"\n📦 Total mnemonic valid yang dimuat: {len(cleaned_mnemonics)}")
    return cleaned_mnemonics


# --- Fungsi Cek Koneksi RPC ---

def cek_semua_rpc():
    print("\n🔌 Mengecek koneksi ke semua jaringan EVM...\n")
    gagal_evm = []
    for name, url in EVM_NETWORKS.items():
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 10}))
            if w3.is_connected():
                print(f"🟢 {name.upper():<10} - Terhubung (Block #{w3.eth.block_number})")
            else:
                print(f"🔴 {name.upper():<10} - GAGAL koneksi: RPC tidak merespons.")
                gagal_evm.append(name)
        except requests.exceptions.ConnectionError:
            print(f"🔴 {name.upper():<10} - Error koneksi: Periksa URL RPC atau koneksi internet.")
            gagal_evm.append(name)
        except Exception as e:
            print(f"🔴 {name.upper():<10} - Error tak terduga: {str(e)}")
            gagal_evm.append(name)
    
    if not gagal_evm:
        print("\n✅ Semua RPC EVM aman!")
    else:
        print(f"\n⚠️ Ada {len(gagal_evm)} jaringan EVM yang gagal terhubung: {', '.join(gagal_evm)}")

    print("\n🔌 Mengecek koneksi ke jaringan TRON...\n")
    try:
        client = Tron()
        _ = client.get_latest_block() 
        print("🟢 TRON - Terhubung")
    except Exception as e:
        print(f"🔴 TRON - GAGAL koneksi: {e}")
        print("Pastikan node Tron berjalan atau konfigurasi TronPy benar (default mainnet).")
    print("\n")

# --- Fungsi Scan Token Kustom (EVM) ---

def scan_custom_token_evm():
    print("\n--- Scan Token Kustom di Jaringan EVM ---")
    print("Pilih jaringan EVM untuk scan:")
    for i, (chain, rpc) in enumerate(EVM_NETWORKS.items(), 1):
        print(f"{i}. {chain.upper()}")
    
    try:
        idx_choice = int(input("Masukkan nomor jaringan: "))
        if not (1 <= idx_choice <= len(EVM_NETWORKS)):
            print("Pilihan nomor jaringan tidak valid.")
            return
        chain_name = list(EVM_NETWORKS.keys())[idx_choice - 1]
        rpc_url = EVM_NETWORKS[chain_name]
    except ValueError:
        print("Input tidak valid. Masukkan angka.")
        return
    except IndexError:
        print("Pilihan nomor jaringan tidak valid.")
        return

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 60}))
    if not w3.is_connected():
        print(f"❌ Gagal koneksi ke jaringan {chain_name}. Pastikan RPC valid dan koneksi stabil.")
        return

    contract_input = input("Masukkan alamat smart contract token (contoh: 0xdAC17F958D2ee523a2206206994597C13D831ec7): ").strip()
    try:
        checksum_address = w3.to_checksum_address(contract_input)
    except ValueError:
        print("❌ Alamat smart contract tidak valid. Pastikan formatnya benar.")
        return

    token_contract = None
    token_name = "Unknown Token"
    token_decimals = 18 

    try:
        token_contract = w3.eth.contract(address=checksum_address, abi=ERC20_ABI)
        _ = token_contract.functions.balanceOf("0x0000000000000000000000000000000000000000").call() # Test call
        token_name = token_contract.functions.name().call()
        token_decimals = token_contract.functions.decimals().call()
        print(f"\n🪙 Token Ditemukan: {token_name} (decimals: {token_decimals})\n")
    except Exception as e:
        print(f"❌ Gagal membaca kontrak token atau alamat bukan kontrak ERC20 valid: {e}")
        print("Pastikan alamat kontrak benar dan Anda memilih jaringan yang sesuai.")
        return

    print("\nPilih Sumber Data Wallet untuk Scan Token:")
    print("1. Dari Mnemonic Phrases (phrases.txt)")
    print("2. Dari Private Keys (privatekeyevm.txt)")
    source_choice = input("Pilih sumber (1/2): ").strip()

    wallets_for_scan = []
    source_type_for_scan = ""

    if source_choice == "1":
        phrases = load_and_clean_phrases()
        if not phrases:
            print("Tidak ada mnemonic yang valid ditemukan di phrases.txt. Kembali ke menu utama.")
            return
        for i, phrase in enumerate(phrases):
            try:
                acct = Account.from_mnemonic(phrase)
                private_key_derived = "0x" + acct.key.hex()
                wallets_for_scan.append({"phrase": phrase, "address": acct.address, "private_key": private_key_derived, "index": i + 1})
            except Exception as e:
                write_to_file(INVALID_MNEMONIC_FILE, f"INVALID MNEMONIC (EVM for Scan Token): {phrase} -> {e}")
                continue
        source_type_for_scan = "Mnemonic Phrase"

    elif source_choice == "2":
        try:
            with open(PRIVATEKEY_EVM_FILE, "r") as f:
                private_keys_raw = [line.strip() for line in f if line.strip()]
                private_keys = []
                for line in private_keys_raw:
                    if re.fullmatch(r'(0x)?[0-9a-fA-F]{64}', line, re.IGNORECASE):
                        private_keys.append(line if line.startswith('0x') else '0x' + line)
                    else:
                        match_old_format = re.search(r'Private Key: (0x[0-9a-fA-F]{64})', line, re.IGNORECASE)
                        if match_old_format:
                            private_keys.append(match_old_format.group(1))

            if not private_keys:
                print(f"❌ Tidak ada private key yang valid ditemukan di '{PRIVATEKEY_EVM_FILE}'. Kembali ke menu utama.")
                return
        except FileNotFoundError:
            print(f"❌ File '{PRIVATEKEY_EVM_FILE}' tidak ditemukan. Silakan generate private key EVM terlebih dahulu. Kembali ke menu utama.")
            return
        for i, pk_hex in enumerate(private_keys):
            try:
                acct = Account.from_key(pk_hex)
                wallets_for_scan.append({"private_key": pk_hex, "address": acct.address, "index": i + 1})
            except Exception as e:
                write_to_file(INVALID_MNEMONIC_FILE, f"INVALID EVM PRIVATE KEY (for Scan Token): {pk_hex} -> {e}")
                continue
        source_type_for_scan = "Private Key"
    else:
        print("Pilihan sumber data tidak valid. Kembali ke menu utama.")
        return

    if not wallets_for_scan:
        print("Tidak ada wallet yang bisa di-scan. Kembali ke menu utama.")
        return

    wallets_with_token = []
    print(f"\n🚀 Memulai scan {token_name} untuk {len(wallets_for_scan)} wallet (via {source_type_for_scan})...\n")
    
    for wallet in wallets_for_scan:
        address = wallet['address']
        private_key_found = wallet.get('private_key', 'N/A') 
        wallet_idx = wallet['index']
        try:
            raw_balance = token_contract.functions.balanceOf(address).call()
            balance = raw_balance / (10 ** token_decimals)
            status_indicator = "✅" if balance > 0 else " "
            print(f"[{wallet_idx}] {status_indicator} {address} : {balance:.4f} {token_name}")
            
            if balance > 0:
                wallets_with_token.append({
                    "private_key": private_key_found, 
                    "address": address,
                    "balance": balance,
                    "token_name": token_name,
                    "token_contract_address": checksum_address, # Simpan alamat kontrak!
                    "token_decimals": token_decimals, # Simpan desimal token!
                    "chain": chain_name
                })
        except Exception as e:
            print(f"[{wallet_idx}] ⚠️ Gagal memproses wallet {address} (dari {private_key_found[:20]}...): {e}")
        time.sleep(1)

    if wallets_with_token:
        print(f"\n--- Ditemukan {len(wallets_with_token)} wallet dengan {token_name} > 0 ---")
        output_filename = f"{EVM_OUTPUT_FILE_PREFIX}{token_name.lower().replace(' ', '_')}_{chain_name}.txt"
        with open(output_filename, "w") as f:
            for data in wallets_with_token:
                # Format baru dengan label eksplisit dan desimal token
                f.write(f"Private Key: {data['private_key']} | Address: {data['address']} | Balance: {data['balance']:.4f} {data['token_name']} | Contract: {data['token_contract_address']} | Decimals: {data['token_decimals']} | Jaringan: {data['chain']}\n")
        print(f"✅ Detail disimpan ke {output_filename}\n")
    else:
        print("\n📭 Tidak ada wallet dengan token tersebut ditemukan.\n")

# --- Fungsi Generate Wallet ---

def generate_wallet_phrase_evm(count):
    print(f"\nGenerasi {count} mnemonic phrase EVM...")
    generated_count = 0
    with open(PHRASE_FILE, "a") as f_phrase:
        for _ in range(count):
            try:
                acct, mnemonic = Account.create_with_mnemonic()
                f_phrase.write(f"{mnemonic}\n")
                generated_count += 1
            except Exception as e:
                print(f"Gagal generate EVM mnemonic: {e}")
    print(f"✅ {generated_count} mnemonic EVM telah digenerate dan disimpan ke {PHRASE_FILE}\n")

def generate_wallet_phrase_tron(count):
    print("\n⛔️ Generate wallet phrase untuk TRON tidak didukung secara langsung seperti EVM.")
    print("   Untuk TRON, mnemonic umumnya berasal dari BIP39 dan kemudian digunakan untuk derivasi private key.")
    print("   Kami hanya dapat generate private key acak untuk TRON.")
    confirm = input("Apakah Anda ingin melanjutkan dengan generate private key TRON sebagai gantinya? (y/n): ").strip().lower()

    if confirm != 'y':
        print("Kembali ke menu sebelumnya.")
        return

    print(f"\nMelanjutkan dengan generasi {count} private key TRON...")
    generated_count = 0
    with open(PRIVATEKEY_TRON_FILE, "a") as f_tron:
        for _ in range(count):
            try:
                private_key = TronPrivateKey(os.urandom(32))
                f_tron.write(f"{private_key.hex()}\n")
            
                generated_count += 1
            except Exception as e:
                print(f"Gagal generate TRON private key: {e}")
    print(f"✅ {generated_count} private key TRON telah digenerate dan disimpan ke {PRIVATEKEY_TRON_FILE}\n")


def generate_wallet_private_key_evm(count):
    """Menghasilkan sejumlah wallet EVM (private key) dan menyimpannya."""
    print(f"\nGenerasi {count} private key EVM...")
    generated_count = 0
    with open(PRIVATEKEY_EVM_FILE, "a") as f_evm:
        for _ in range(count):
            try:
                acct = Account.create()
                private_key = "0x" + acct.key.hex()
                f_evm.write(f"{private_key}\n") 
                generated_count += 1
            except Exception as e:
                print(f"Gagal generate EVM private key: {e}")
    print(f"✅ {generated_count} private key EVM telah digenerate dan disimpan ke {PRIVATEKEY_EVM_FILE}\n")

def generate_wallet_private_key_tron(count):
    """Menghasilkan sejumlah wallet TRON (private key) dan menyimpannya."""
    print(f"\nGenerasi {count} private key TRON...")
    generated_count = 0
    with open(PRIVATEKEY_TRON_FILE, "a") as f_tron:
        for _ in range(count):
            try:
                private_key_obj = TronPrivateKey(os.urandom(32))
                f_tron.write(f"{private_key_obj.hex()}\n")
                generated_count += 1
            except Exception as e:
                print(f"Gagal generate TRON private key: {e}")
    print(f"✅ {generated_count} private key TRON telah digenerate dan disimpan ke {PRIVATEKEY_TRON_FILE}\n")

# ===== File paths for the new Menu 3 (Address Checker) =====
PK_TRON_FILE = "privatekeytron.txt"
PK_EVM_FILE = "privatekeyevm.txt"
PHRASE_FILE = "phrases.txt"
ADDR_EVM_OUT = "addresevm.txt"
ADDR_TRON_OUT = "addrestron.txt"

def load_lines(filename):
    if not os.path.exists(filename):
        print(f"❌ File '{filename}' tidak ditemukan.")
        return []
    with open(filename, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def scan_private_keys_tron_new():
    print("\n[🔍] Memeriksa Private Key TRON dan mendapatkan alamatnya:")
    private_keys = load_lines(PK_TRON_FILE)
    found_addresses = []
    if not private_keys:
        print(f"Tidak ada private key TRON ditemukan di '{PK_TRON_FILE}'.")
        return

    for i, pk in enumerate(private_keys):
        try:
            key = TronPrivateKey(bytes.fromhex(pk if pk.startswith('0x') else pk))
            address = key.public_key.to_base58check_address()
            print(f"[{i+1}] ✅ PrivateKey: {pk[:10]}... | Address: {address}")
            found_addresses.append(address)
        except Exception as e:
            print(f"[{i+1}] ❌ Private Key TRON tidak valid: {pk[:10]}... | Error: {e}")
    
    if found_addresses:
        with open(ADDR_TRON_OUT, 'w') as f:
            for addr in found_addresses:
                f.write(addr + "\n")
        print(f"\n📁 Semua alamat TRON yang ditemukan telah disimpan ke: {ADDR_TRON_OUT}")
    else:
        print("\n📭 Tidak ada alamat TRON valid yang ditemukan dari private key.")

def scan_private_keys_evm_new():
    print("\n[🔍] Memeriksa Private Key EVM dan mendapatkan alamatnya:")
    private_keys = load_lines(PK_EVM_FILE)
    found_addresses = []
    if not private_keys:
        print(f"Tidak ada private key EVM ditemukan di '{PK_EVM_FILE}'.")
        return

    for i, pk in enumerate(private_keys):
        if not pk.startswith("0x"):
            pk_formatted = "0x" + pk
        else:
            pk_formatted = pk

        try:
            acct = Account.from_key(pk_formatted)
            print(f"[{i+1}] ✅ PrivateKey: {pk_formatted[:10]}... | Address: {acct.address}")
            found_addresses.append(acct.address)
        except Exception as e:
            print(f"[{i+1}] ❌ Private Key EVM tidak valid: {pk_formatted[:10]}... | Error: {e}")
    
    if found_addresses:
        with open(ADDR_EVM_OUT, 'w') as f:
            for addr in found_addresses:
                f.write(addr + "\n")
        print(f"\n📁 Semua alamat EVM yang ditemukan telah disimpan ke: {ADDR_EVM_OUT}")
    else:
        print("\n📭 Tidak ada alamat EVM valid yang ditemukan dari private key.")

def scan_phrases_evm_only_new():
    print("\n[🔍] Mengderivasi alamat EVM dari Mnemonic Phrase:")
    phrases = load_lines(PHRASE_FILE)
    mnemo = Mnemonic("english")
    found_addresses = []
    if not phrases:
        print(f"Tidak ada mnemonic phrase ditemukan di '{PHRASE_FILE}'.")
        return

    for i, phrase in enumerate(phrases):
        if not mnemo.check(phrase):
            print(f"[{i+1}] ❌ Phrase tidak valid (checksum error): {phrase[:20]}...")
            continue
        try:
            seed = mnemo.to_seed(phrase, passphrase="") 
            wallet = Wallet(seed) 
            
            evm_private_key_bytes = wallet.derive_account("eth", account=0).private_key()
            evm_address = Account.from_key(evm_private_key_bytes).address
            
            print(f"[{i+1}] ✅ Phrase: {phrase[:20]}... | Address EVM (derived): {evm_address}")
            found_addresses.append(evm_address)
        except Exception as e:
            print(f"[{i+1}] ❌ Gagal memproses phrase untuk EVM: {phrase[:20]}... | Error: {e}")
    
    if found_addresses:
        with open(ADDR_EVM_OUT, 'a') as f: 
            f.write("\n--- Addresses derived from Phrases ---\n")
            for addr in found_addresses:
                f.write(addr + "\n")
        print(f"\n📁 Semua alamat EVM yang ditemukan telah ditambahkan ke: {ADDR_EVM_OUT}")
    else:
        print("\n📭 Tidak ada alamat EVM valid yang berhasil diderivasi dari mnemonic phrase.")


# --- FUNGSI INTI PENGIRIMAN TOKEN ---
def _perform_token_send(private_key, sender_address, target_address, token_symbol_from_file, token_amount_from_file, token_contract_addr, token_decimals_from_file, chain_name):
    """
    Melakukan transaksi pengiriman token dari satu wallet.
    Akan selalu mengirim MAX saldo yang ditemukan di blockchain untuk token tersebut.
    Menggunakan data token (contract, decimals) dari file hasil scan.
    """
    try:
        rpc_url = EVM_NETWORKS.get(chain_name)
        if not rpc_url:
            print(f"❌ Jaringan '{chain_name}' tidak dikonfigurasi RPC-nya. Melewatkan pengiriman {token_symbol_from_file} dari {sender_address}.")
            return False

        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 60}))
        if not w3.is_connected():
            print(f"❌ Gagal koneksi ke RPC jaringan {chain_name}. Melewatkan pengiriman {token_symbol_from_file} dari {sender_address}.")
            return False

        acct = Account.from_key(private_key)
        
        token_contract_addr_checksum = w3.to_checksum_address(token_contract_addr)
        token_contract = w3.eth.contract(address=token_contract_addr_checksum, abi=ERC20_ABI)
        
        token_decimals = token_decimals_from_file 
        
        actual_token_balance_raw = token_contract.functions.balanceOf(sender_address).call()
        actual_token_balance_human = actual_token_balance_raw / (10**token_decimals)

        if actual_token_balance_raw == 0:
            print(f"ℹ️ Saldo {token_symbol_from_file} dari {sender_address} adalah 0 di blockchain. Melewatkan.")
            return False
        
        gas_price = w3.eth.gas_price 
        gas_limit_erc20 = 70000 
        
        estimated_gas_cost_wei = gas_price * gas_limit_erc20
        native_balance_wei = w3.eth.get_balance(acct.address)
        
        if native_balance_wei < estimated_gas_cost_wei:
            print(f"⚠️ Saldo native coin ({chain_name.upper()}) dari {acct.address} tidak cukup untuk biaya gas ({w3.from_wei(native_balance_wei, 'ether'):.6f} {chain_name.upper()}). Diperlukan sekitar {w3.from_wei(estimated_gas_cost_wei, 'ether'):.6f} {chain_name.upper()}. Melewatkan pengiriman {token_symbol_from_file}.")
            return False
        
        nonce = w3.eth.get_transaction_count(acct.address)

        tx = token_contract.functions.transfer(
            w3.to_checksum_address(target_address), 
            actual_token_balance_raw 
        ).build_transaction({
            'from': acct.address,
            'nonce': nonce,
            'gas': gas_limit_erc20, 
            'gasPrice': gas_price
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        
        tx_hash_result = w3.eth.send_raw_transaction(signed_tx.raw_transaction) 
        
        tx_hash_hex = tx_hash_result.hex() 

        explorer_base_url = BLOCK_EXPLORER_URLS.get(chain_name)
        clickable_tx_url = "N/A"
        if explorer_base_url:
            clickable_tx_url = f"{explorer_base_url}{tx_hash_hex}" 

        print(f"✅ TX sent: {acct.address} -> {token_symbol_from_file} {actual_token_balance_human:.4f} -> {target_address}")
        print(f"   Hash: {tx_hash_hex}") 
        print(f"   Verifikasi: {clickable_tx_url}") 
        
        write_to_file("tx_log.txt", f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] TX_EVM | Chain: {chain_name.upper()} | From: {acct.address} | To: {target_address} | Token: {token_symbol_from_file} {actual_token_balance_human:.4f} | Hash: {tx_hash_hex} | Verifikasi: {clickable_tx_url}")
        return True

    except Exception as e:
        print(f"⚠️ Gagal kirim dari {sender_address} untuk {token_symbol_from_file}: {e}")
        return False

# --- FUNGSI SCAN SALDO TRON STABLECOINS ---
def scan_tron_stablecoins():
    print("\n--- Scan Saldo Stablecoin di Jaringan TRON ---")
    
    wallets_for_scan = []
    client = Tron() # Inisialisasi Tron client
    source_type_for_scan = "Private Key" # Hanya Private Key yang akan digunakan

    # --- PENTING: Penanganan Kunci API TRONGRID ---
    print("\n❗ PERHATIAN: Jika Anda melihat '401 Unauthorized', cek ulang kunci API Trongrid Anda.")
    print("   Pastikan kunci di skrip sama persis dengan yang di Trongrid dan masih aktif.")
    # --- Akhir Penanganan Kunci API TRONGRID ---

    try:
        with open(PRIVATEKEY_TRON_FILE, "r") as f:
            private_keys_raw = [line.strip() for line in f if line.strip()]
            private_keys = []
            for line in private_keys_raw:
                if re.fullmatch(r'[0-9a-fA-F]{64}', line, re.IGNORECASE):
                    private_keys.append(line)
                else:
                    match_old_format = re.search(r'(Private Key: )?([0-9a-fA-F]{64})', line, re.IGNORECASE)
                    if match_old_format:
                        private_keys.append(match_old_format.group(2))

        if not private_keys:
            print(f"❌ Tidak ada private key TRON yang valid ditemukan di '{PRIVATEKEY_TRON_FILE}'. Pastikan file ada dan berisi private key.")
            return
    except FileNotFoundError:
        print(f"❌ File '{PRIVATEKEY_TRON_FILE}' tidak ditemukan. Silakan generate private key TRON terlebih dahulu.")
        return
    except Exception as e:
        print(f"❌ Error saat memuat private key TRON dari '{PRIVATEKEY_TRON_FILE}': {e}")
        return
    
    print(f"\nMemproses {len(private_keys)} private key TRON...")
    for i, pk_hex in enumerate(private_keys):
        try:
            pk_bytes = bytes.fromhex(pk_hex)
            tron_account_obj = TronPrivateKey(pk_bytes)
            tron_address = tron_account_obj.public_key.to_base58check_address()
            wallets_for_scan.append({"private_key": pk_hex, "address": tron_address, "index": i + 1})
        except Exception as e:
            write_to_file(INVALID_MNEMONIC_FILE, f"INVALID TRON PRIVATE KEY (for Scan): {pk_hex} -> {e}")
            print(f"⚠️ Gagal memproses private key TRON '{pk_hex[:30]}...': {e}")
            continue

    if not wallets_for_scan:
        print("Tidak ada wallet TRON yang bisa di-scan dari private key yang dimuat.")
        return

    found_assets = []
    print(f"\n🚀 Memulai scan {len(TRON_STABLECOIN_CONTRACTS)} stablecoin dan TRX untuk {len(wallets_for_scan)} wallet TRON (via {source_type_for_scan})...\n")

    for wallet in wallets_for_scan:
        address_base58 = wallet['address']
        private_key_found = wallet.get('private_key', 'N/A')
        wallet_idx = wallet['index']
        asset_found_for_wallet = False
        
        trx_balance = Decimal('0') # Inisialisasi default ke Decimal 0

        # Cek saldo TRX (native coin)
        try:
            raw_balance_from_api = client.get_account_balance(address_base58)
            
            # --- Perbaikan Konversi Saldo TRX & Output Ringkas ---
            if isinstance(raw_balance_from_api, Decimal): 
                trx_balance = raw_balance_from_api # Jika Decimal, pakai langsung (asumsi sudah TRX)
            elif isinstance(raw_balance_from_api, int):
                trx_balance = Decimal(raw_balance_from_api) / Decimal('1000000') # Convert SUN (int) to TRX (Decimal)
            else: # Fallback for unexpected types
                trx_balance = Decimal('0')
                # Cetak pesan warning jika tipe tidak terduga
                print(f"[{wallet_idx}] ⚠️ Saldo TRX untuk {address_base58} tidak dapat diinterpretasi. (Type: {type(raw_balance_from_api)}).")


            if trx_balance > Decimal('0.0001'): # Check against the threshold using Decimal
                # Output ringkas seperti yang diminta: "saldo wallet X (alamat singkat) berisi Y.YYYY TRX"
                print(f"[{wallet_idx}] Saldo: {trx_balance:.6f} TRX ({address_base58[:6]}...{address_base58[-4:]})")
                found_assets.append(f"TRON | Private Key: {private_key_found} | Address: {address_base58} | Balance: {trx_balance:.6f} TRX | Jaringan: tron")
                asset_found_for_wallet = True
        except Exception as e_native:
            # Tetap cetak error untuk debugging API key yang masih bermasalah
            print(f"[{wallet_idx}] ❌ Gagal cek saldo TRX untuk {address_base58}: {type(e_native).__name__}: {e_native}")
            trx_balance = Decimal('0') # Ensure it's Decimal 0 if error occurs
            pass 

        # Cek stablecoin TRC20
        if TRON_STABLECOIN_CONTRACTS:
            for symbol, contract_address_base58 in TRON_STABLECOIN_CONTRACTS.items():
                try:
                    token_contract = client.get_contract(contract_address_base58)
                    token_decimals = token_contract.functions.decimals() # TronPy returns value directly
                    raw_token_balance_from_api = token_contract.functions.balanceOf(address_base58) # TronPy returns value directly
                    
                    # Konversi saldo token TRC20 (asumsi raw_token_balance_from_api juga bisa Decimal atau int)
                    if isinstance(raw_token_balance_from_api, Decimal):
                        token_balance = raw_token_balance_from_api / (Decimal('10')**token_decimals)
                    elif isinstance(raw_token_balance_from_api, int):
                        token_balance = Decimal(raw_token_balance_from_api) / (Decimal('10')**token_decimals)
                    else:
                        token_balance = Decimal('0')
                        # Cetak pesan warning jika tipe tidak terduga
                        print(f"[{wallet_idx}] ⚠️ Saldo {symbol} untuk {address_base58} tidak dapat diinterpretasi. (Type: {type(raw_token_balance_from_api)}).")


                    if token_balance > Decimal('0.0001'): # Check using Decimal for consistency
                        # Output ringkas seperti yang diminta: "saldo wallet X (alamat singkat) berisi Y.YYYY USDT"
                        print(f"[{wallet_idx}] Saldo: {token_balance:.4f} {symbol} ({address_base58[:6]}...{address_base58[-4:]})")
                        found_assets.append(f"TRON | Private Key: {private_key_found} | Address: {address_base58} | Balance: {token_balance:.4f} {symbol} | Contract: {contract_address_base58} | Decimals: {token_decimals} | Jaringan: tron")
                        asset_found_for_wallet = True
                except Exception as e_token:
                    # Ini adalah debugging print yang bisa dihilangkan di versi final
                    # print(f"[{wallet_idx}] DEBUG: Gagal cek saldo {symbol} untuk {address_base58}: {type(e_token).__name__}: {e_token}")
                    pass 

        if not asset_found_for_wallet and trx_balance <= Decimal('0.0001'):
            pass # Tidak ada aset signifikan ditemukan, jadi tidak perlu mencetak "saldo 0" atau "tidak terdeteksi"

        time.sleep(1) # Jeda setelah setiap wallet dicek

    if found_assets:
        print("\n--- Ringkasan Wallet Berisi Aset TRON ---")
        with open(TRON_OUTPUT_FILE, "w") as f:
            for entry in found_assets:
                print(entry)
                f.write(entry + "\n")
        print(f"\n✅ Detail disimpan ke {TRON_OUTPUT_FILE}\n")
    else:
        print("\n📭 Tidak ada wallet TRON yang berisi aset signifikan.\n") # Ini akan tercetak jika tidak ada wallet di atas ambang batas.

# --- FUNGSI UTAMA KIRIM TOKEN ---
def send_detected_tokens():
    print("\n=== Kirim Token dari Wallet yang Terdeteksi ===")
    folder = "."
    token_files = [f for f in os.listdir(folder) if f.startswith(EVM_OUTPUT_FILE_PREFIX) and f.endswith(".txt")]

    if not token_files:
        print("❌ Tidak ada file hasil scan token EVM ditemukan (misal: 'wallet_berisi_usdt_bsc.txt').")
        print("   Silakan jalankan Menu No.1 terlebih dahulu untuk membuat file hasil scan.")
        return

    print("\nPilih file hasil scan token:")
    for idx, fname in enumerate(token_files, 1):
        print(f"{idx}. {fname}")
    
    print(f"{len(token_files) + 1}. Kirim SEMUA token dari SEMUA file yang terdeteksi.")

    try:
        choice_str = input("Masukkan nomor pilihan: ").strip()
        
        target_address = input("Masukkan alamat tujuan pengiriman token (EVM): ").strip()
        if not Web3.is_address(target_address):
            print("❌ Alamat tujuan tidak valid. Pastikan formatnya EVM (dimulai dengan 0x dan 42 karakter).")
            return

        wallets_to_process = []
        
        if choice_str.isdigit() and int(choice_str) == len(token_files) + 1: 
            print("\nMemuat data dari SEMUA file hasil scan...\n")
            for selected_file_path in token_files:
                try:
                    with open(selected_file_path, "r") as f:
                        lines = [line.strip() for line in f if line.strip()]
                        for line in lines:
                            wallets_to_process.append( line ) 
                except Exception as e:
                    print(f"⚠️ Gagal membaca file {selected_file_path}: {e}")
            if not wallets_to_process:
                print("Tidak ada data token yang valid ditemukan di semua file yang terpilih.")
                return
        elif choice_str.isdigit() and 1 <= int(choice_str) <= len(token_files): 
            selected_file_path = token_files[int(choice_str) - 1]
            print(f"\nMemuat data dari file '{selected_file_path}'...\n")
            try:
                with open(selected_file_path, "r") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    for line in lines:
                        wallets_to_process.append( line )
            except Exception as e:
                print(f"⚠️ Gagal membaca file {selected_file_path}: {e}")
            if not wallets_to_process:
                print("Tidak ada data token yang valid ditemukan di file ini.")
                return
        else:
            print("❌ Pilihan tidak valid. Silakan masukkan nomor yang benar.")
            return

        print(f"\n🚀 Memulai transaksi pengiriman ke {target_address}...\n")
        
        successful_sends = 0
        failed_sends = 0

        for line in wallets_to_process:
            try:
                parts_dict = {}
                for item in line.split('|'):
                    if ':' in item:
                        key, value = item.split(':', 1)
                        parts_dict[key.strip()] = value.strip()
                
                private_key = parts_dict.get("Private Key")
                sender_address = parts_dict.get("Address")
                balance_info = parts_dict.get("Balance") 
                token_contract_addr = parts_dict.get("Contract") 
                token_decimals_str = parts_dict.get("Decimals") 
                chain_name = parts_dict.get("Jaringan", "").lower()

                if not all([private_key, sender_address, balance_info, token_contract_addr, token_decimals_str, chain_name]):
                    print(f"⚠️ Baris dengan format tidak lengkap atau tidak memiliki semua info yang diperlukan: {line}. Melewatkan.")
                    failed_sends += 1
                    continue

                try:
                    token_decimals = int(token_decimals_str) 
                except ValueError:
                    print(f"⚠️ Desimal token tidak valid di baris: '{line}'. Melewatkan.")
                    failed_sends += 1
                    continue


                balance_parts = balance_info.split()
                if len(balance_parts) < 2:
                    print(f"⚠️ Format saldo tidak valid di baris: '{line}'. Melewatkan.")
                    failed_sends += 1
                    continue
                
                token_amount_from_file = float(balance_parts[0])
                token_symbol_from_file = balance_parts[1].upper()

                if token_symbol_from_file == chain_name.upper() or "NATIVE" in balance_info.upper() or token_amount_from_file == 0:
                    if token_amount_from_file == 0:
                         print(f"ℹ️ Melewatkan {token_symbol_from_file} dari {sender_address} karena saldo terdeteksi di file adalah 0.")
                    else: 
                        print(f"ℹ️ Melewatkan {token_symbol_from_file} (Native Coin) dari {sender_address}. Fungsi ini untuk token ERC20.")
                    continue
                
                print(f"\nProcessing: {sender_address} | {token_amount_from_file:.4f} {token_symbol_from_file} ({chain_name})...")
                
                if _perform_token_send(private_key, sender_address, target_address, token_symbol_from_file, token_amount_from_file, token_contract_addr, token_decimals, chain_name):
                    successful_sends += 1
                else:
                    failed_sends += 1
                
                time.sleep(2) 

            except Exception as e:
                print(f"⚠️ Error memproses baris '{line}': {e}")
                failed_sends += 1
                continue

        print(f"\n--- Ringkasan Pengiriman ---")
        print(f"✅ Transaksi berhasil: {successful_sends}")
        print(f"❌ Transaksi gagal: {failed_sends}")
        print("-" * 30)

    except ValueError:
        print("❌ Input pilihan tidak valid. Masukkan angka.")
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")

# --- Menu Utama Aplikasi ---

def main_menu():
    """Menampilkan menu utama dan memproses pilihan pengguna."""
    while True:
        print("\n" + "="*30)
        print("=== APLIKASI SCAN & TRANSFER WALLET ===")
        print("="*30)
        print("0. Tes semua koneksi jaringan (RPC EVM & TRON)")
        print("1. Scan token kustom menggunakan smart contract (EVM)")
        print("2. Kirim token dari wallet yang terdeteksi (EVM only)") 
        print("3. Generate wallet baru")
        print("4. Cek Alamat Wallet (Private Key/Mnemonic)")
        print("5. Scan Saldo Stablecoin TRON") # OPSI BARU UNTUK SCAN TRON STABLECOINS
        print("6. Validasi & Bersihkan mnemonic phrases dari file")
        print("7. Keluar") # Nomor Exit berubah
        print("="*30)

        pilihan = input("Pilih menu: ").strip()
        print("\n")

        if pilihan == "0":
            cek_semua_rpc()
        elif pilihan == "1":
            scan_custom_token_evm()
        elif pilihan == "2":
            send_detected_tokens()
        elif pilihan == "3":
            try:
                print("\nPilih jenis generate:")
                print("1. Generate Wallet Phrase (Mnemonic)")
                print("2. Generate Private Key")
                generate_type_choice = input("Pilih (1/2): ").strip()

                if generate_type_choice == "1":
                    print("\nPilih jaringan untuk generate Wallet Phrase:")
                    print("1. EVM")
                    print("2. TRON") 
                    network_choice = input("Pilih (1/2): ").strip()

                    try:
                        jumlah = int(input("Masukkan jumlah wallet (phrase) yang ingin digenerate: "))
                    except ValueError:
                        print("Input jumlah tidak valid. Masukkan angka.")
                        continue 

                    if network_choice == "1":
                        generate_wallet_phrase_evm(jumlah)
                    elif network_choice == "2":
                        generate_wallet_phrase_tron(jumlah) 
                    else:
                        print("Pilihan jaringan tidak valid.")
                
                elif generate_type_choice == "2":
                    print("\nPilih jaringan untuk generate Private Key:")
                    print("1. EVM")
                    print("2. TRON")
                    network_choice = input("Pilih (1/2): ").strip()

                    try:
                        jumlah = int(input("Masukkan jumlah private key yang ingin digenerate: "))
                    except ValueError:
                        print("Input jumlah tidak valid. Masukkan angka.")
                        continue 

                    if network_choice == "1":
                        generate_wallet_private_key_evm(jumlah)
                    elif network_choice == "2":
                        generate_wallet_private_key_tron(jumlah)
                    else:
                        print("Pilihan jaringan tidak valid.")
                else:
                    print("Pilihan jenis generate tidak valid. Pilih '1' (Wallet Phrase) atau '2' (Private Key).")
            except Exception as e:
                print(f"Terjadi kesalahan saat generate wallet: {e}")
        elif pilihan == "4":
            print("\n--- Cek Alamat Wallet ---")
            print("Pilih sumber data:")
            print("1. Private Key (TRON)")
            print("2. Private Key (EVM)")
            print("3. Mnemonic Phrase (EVM only)")
            address_check_choice = input("Pilih jenis cek alamat (1-3): ").strip()

            if address_check_choice == "1":
                scan_private_keys_tron_new()
            elif address_check_choice == "2":
                scan_private_keys_evm_new()
            elif address_check_choice == "3":
                scan_phrases_evm_only_new()
            else:
                print("Pilihan tidak valid.")
        elif pilihan == "5": # OPSI BARU UNTUK SCAN TRON
            scan_tron_stablecoins()
        elif pilihan == "6": # Nomor opsi Validasi berubah
            print("Memvalidasi mnemonic dari 'phrases.txt'...")
            load_and_clean_phrases(show_detail=True)
            print("\nProses validasi selesai. Harap cek 'invalid_mnemonics.txt' untuk detail mnemonic yang tidak valid.")
        elif pilihan == "7": # Nomor opsi Keluar berubah
            print("Terima kasih telah menggunakan aplikasi ini. Sampai jumpa!")
            sys.exit()
        else:
            print("Pilihan tidak valid. Silakan coba lagi.")


if __name__ == "__main__":
    main_menu()
