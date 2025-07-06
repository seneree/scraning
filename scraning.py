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
from decimal import Decimal
import warnings

# --- PUSTAKA SOLANA (YANG SUDAH DIPERBAIKI) ---
import base58
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import transfer, TransferParams
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
    transfer as spl_transfer,
    TransferParams as SplTransferParams,
    TOKEN_PROGRAM_ID
)

warnings.filterwarnings("ignore")
Account.enable_unaudited_hdwallet_features()

# --- KONFIGURASI FILE ---
PHRASE_FILE = "phrases.txt"
INVALID_MNEMONIC_FILE = "invalid_mnemonics.txt"
EVM_OUTPUT_FILE_PREFIX = "wallet_berisi_"
PRIVATEKEY_EVM_FILE = "privatekeyevm.txt"
PRIVATEKEY_TRON_FILE = "privatekeytron.txt"
PRIVATEKEY_SOL_FILE = "privatekeysol.txt"
ADDR_EVM_OUT = "addresevm.txt"
ADDR_TRON_OUT = "addrestron.txt"
ADDR_SOL_OUT = "addressol.txt"

# --- KUNCI API & RPC ---
TRONGRID_API_KEY = ""
HELIUS_API_KEY = ""

os.environ['TRONGRID_API_KEY'] = TRONGRID_API_KEY
EVM_NETWORKS = {
    "ethereum": "https://eth-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW", "bsc": "https://bnb-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW", "polygon": "https://polygon-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW", "arbitrum": "https://arb-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW", "optimism": "https://opt-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW", "avalanche": "https://avax-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW", "base": "https://base-mainnet.g.alchemy.com/v2/56hawCppdeNWhxYEHqzM0yut_wrN_zaW", "linea": "https://rpc.linea.build", "zksync": "https://mainnet.era.zksync.io", "scroll": "https://rpc.scroll.io", "blast": "https://rpc.blast.io"
}
RPC_URL_SOL = "https://api.mainnet-beta.solana.com"
solana_client = Client(RPC_URL_SOL)

# --- BLOCK EXPLORER URLS ---
BLOCK_EXPLORER_URLS = {
    "ethereum": "https://etherscan.io/tx/", "bsc": "https://bscscan.com/tx/", "polygon": "https://polygonscan.com/tx/", "arbitrum": "https://arbiscan.io/tx/", "optimism": "https://optimistic.etherscan.io/tx/", "avalanche": "https://snowtrace.io/tx/", "base": "https://basescan.org/tx/", "tron": "https://tronscan.org/#/transaction/", "solana": "https://solscan.io/tx/", "linea": "https://lineascan.build/tx/", "zksync": "https://explorer.zksync.io/tx/", "scroll": "https://scrollscan.com/tx/", "blast": "https://blastscan.io/tx/"
}

# --- ABI ---
ERC20_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}]')

# --- FUNGSI-FUNGSI PEMBANTU (UTILITIES) ---
def is_valid_mnemonic_length(words):
    return len(words) in [12, 15, 18, 21, 24]

def write_to_file(filename, content):
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(content + "\n")

def load_lines(filename):
    if not os.path.exists(filename):
        print(f"❌ File '{filename}' tidak ditemukan.")
        return []
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        return [line.strip() for line in f if line.strip()]

def load_and_clean_phrases(file_path=PHRASE_FILE, show_detail=False):
    try:
        with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' tidak ditemukan. Pastikan ada.")
        return []
    except Exception as e:
        print(f"❌ Error: Gagal membaca file '{file_path}': {e}")
        return []
    cleaned_mnemonics = []
    invalid_mnemonics_buffer = []
    if show_detail: print(f"\n--- Memulai validasi mnemonic dari '{file_path}' ---")
    for line_num, line in enumerate(lines, 1):
        original_line = line
        if ':' in line: line = line.split(":", 1)[1].strip()
        words = line.split()
        if not words: continue
        try:
            if not is_valid_mnemonic_length(words): raise ValueError(f"Panjang mnemonic tidak valid ({len(words)} kata).")
            mnemo = Mnemonic("english")
            if not mnemo.check(line): raise ValueError("Checksum mnemonic tidak valid.")
            cleaned_mnemonics.append(line)
            if show_detail: print(f"✅ Baris {line_num}: Mnemonic valid ({len(words)} kata): {line[:50]}...")
        except Exception as e:
            error_message = f"Baris {line_num}: '{original_line}' -> Error: {e}"
            invalid_mnemonics_buffer.append(error_message)
            if show_detail: print(f"⚠️ Baris {line_num}: Mnemonic tidak valid: '{original_line[:50]}...' -> {e}")
    if invalid_mnemonics_buffer:
        print(f"\n--- Ditemukan {len(invalid_mnemonics_buffer)} mnemonic tidak valid. ---")
        print(f"Detail mnemonic yang tidak valid disimpan ke '{INVALID_MNEMONIC_FILE}'")
        for inv_mnemonic in invalid_mnemonics_buffer: write_to_file(INVALID_MNEMONIC_FILE, inv_mnemonic)
        if show_detail: print("-" * 40)
    elif show_detail: print("\n🎉 Semua mnemonic di file valid!")
    if show_detail: print(f"\n📦 Total mnemonic valid yang dimuat: {len(cleaned_mnemonics)}")
    return cleaned_mnemonics

# --- FUNGSI-FUNGSI SOLANA ---
def get_spl_token_info(mint_address: str) -> dict:
    if HELIUS_API_KEY == "GANTI_DENGAN_KUNCI_API_HELIUS_ANDA" or len(HELIUS_API_KEY) < 10:
        print("⚠️ Peringatan: Kunci API Helius belum diatur. Nama token mungkin tidak akurat.")
        return {"name": f"Token-{mint_address[:4]}", "symbol": f"TKN-{mint_address[:4]}"}
    api_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {"jsonrpc": "2.0", "id": "helius-test", "method": "getAsset", "params": {"id": mint_address}}
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        content = data.get('result', {}).get('content', {})
        metadata = content.get('metadata', {})
        if metadata and metadata.get('symbol'):
            return {"name": metadata.get("name", f"Token-{mint_address[:4]}"), "symbol": metadata.get("symbol", f"TKN-{mint_address[:4]}")}
        else:
            return {"name": f"Token-{mint_address[:4]}", "symbol": f"TKN-{mint_address[:4]}"}
    except Exception as e:
        print(f" Gagal mengambil metadata dari Helius: {e}")
        return {"name": f"Token-{mint_address[:4]}", "symbol": f"TKN-{mint_address[:4]}"}

def generate_wallet_private_key_sol(count):
    print(f"\nGenerasi {count} private key Solana...")
    with open(PRIVATEKEY_SOL_FILE, "a", encoding='utf-8') as f:
        for _ in range(count):
            f.write(f"{str(Keypair())}\n")
    print(f"✅ {count} private key Solana telah disimpan ke {PRIVATEKEY_SOL_FILE}\n")

def scan_private_keys_sol_new():
    print("\n[🔍] Memeriksa Private Key Solana dan mendapatkan alamatnya:")
    private_keys = load_lines(PRIVATEKEY_SOL_FILE)
    if not private_keys: return
    with open(ADDR_SOL_OUT, 'w', encoding='utf-8') as f:
        for i, pk_b58 in enumerate(private_keys, 1):
            try:
                keypair = Keypair.from_base58_string(pk_b58)
                address = str(keypair.pubkey())
                print(f"[{i}] ✅ PrivateKey: {pk_b58[:15]}... | Address: {address}")
                f.write(address + "\n")
            except Exception as e:
                print(f"[{i}] ❌ Private Key Solana tidak valid: {pk_b58[:15]}... | Error: {e}")
    print(f"\n📁 Alamat Solana disimpan ke: {ADDR_SOL_OUT}")

def cek_saldo_sol(client: Client, address: str):
    try:
        wallet_pubkey = Pubkey.from_string(address)
        balance_sol = client.get_balance(wallet_pubkey).value / 1_000_000_000
        print(f"\n✅ Informasi Saldo SOL\n==========================\nAlamat: {address}\nSaldo : {balance_sol:.9f} SOL\n==========================")
    except Exception as e:
        print(f"❌ Gagal memeriksa saldo SOL: {e}")

def cek_saldo_spl(client: Client, wallet_address: str, token_mint_address: str):
    try:
        wallet_pubkey = Pubkey.from_string(wallet_address)
        token_mint_pubkey = Pubkey.from_string(token_mint_address)
        ata = get_associated_token_address(wallet_pubkey, token_mint_pubkey)
        balance = int(client.get_token_account_balance(ata).value.amount) / (10 ** client.get_token_account_balance(ata).value.decimals)
        print(f"\n✅ Informasi Saldo Token SPL\n===================================\nAlamat Wallet: {wallet_address}\nAlamat Mint Token: {token_mint_address}\nSaldo Token: {balance}\n===================================")
    except Exception:
        print("\n❌ Gagal memeriksa saldo token SPL. Pastikan alamat benar atau wallet belum pernah memiliki token tsb.")

def scan_sol_balance_massal(client: Client):
    print("\n--- Scan Saldo SOL Massal ---")
    private_keys = load_lines(PRIVATEKEY_SOL_FILE)
    if not private_keys:
        print(f"⚠️ Proses dihentikan karena tidak ada data di '{PRIVATEKEY_SOL_FILE}'.")
        input("Tekan Enter untuk kembali ke menu...")
        return
    print(f"🚀 Memulai scan saldo SOL untuk {len(private_keys)} wallet dari '{PRIVATEKEY_SOL_FILE}'...")
    wallets_with_sol = []
    output_filename = "wallet_berisi_sol.txt"
    if os.path.exists(output_filename):
        os.remove(output_filename)
    for i, pk_b58 in enumerate(private_keys, 1):
        try:
            keypair = Keypair.from_base58_string(pk_b58)
            address = keypair.pubkey()
            balance_sol = client.get_balance(address).value / 1_000_000_000
            status = "✅" if balance_sol > 0 else " "
            print(f"[{i}] {status} {address} : {balance_sol:.9f} SOL")
            if balance_sol > 0:
                wallets_with_sol.append(f"PrivateKey: {pk_b58} | Address: {address} | Balance: {balance_sol:.9f} SOL")
            time.sleep(0.5)
        except Exception as e:
            print(f"[{i}] ⚠️ Gagal memproses key: {pk_b58[:15]}... | Error: {e}")
    if wallets_with_sol:
        print(f"\n--- Ditemukan {len(wallets_with_sol)} wallet dengan saldo SOL > 0 ---")
        write_to_file(output_filename, "\n".join(wallets_with_sol))
        print(f"✅ Detail disimpan ke {output_filename}")
    else:
        print("\n📭 Tidak ada wallet dengan saldo SOL yang ditemukan.")

def scan_spl_token_massal(client: Client):
    print("\n--- Scan Saldo Token SPL Massal ---")
    token_mint_address = input("Masukkan alamat MINT token SPL yang ingin di-scan: ").strip()
    if not token_mint_address:
        print("Alamat mint tidak boleh kosong.")
        return
    private_keys = load_lines(PRIVATEKEY_SOL_FILE)
    if not private_keys:
        print(f"⚠️ Proses dihentikan karena tidak ada data di '{PRIVATEKEY_SOL_FILE}'.")
        input("Tekan Enter untuk kembali ke menu...")
        return
    try:
        token_mint_pubkey = Pubkey.from_string(token_mint_address)
        print("ℹ️ Mengambil info token dari internet...")
        token_info = get_spl_token_info(token_mint_address)
        token_symbol = token_info['symbol']
        token_name = token_info['name']
        print(f"✅ Token teridentifikasi: {token_name} ({token_symbol})")
    except Exception as e:
        print(f"❌ Alamat mint token tidak valid: {e}")
        return
    print(f"🚀 Memulai scan token {token_symbol} untuk {len(private_keys)} wallet...")
    wallets_with_spl = []
    output_filename = f"wallet_berisi_{token_symbol.lower().replace(' ', '_')}_solana.txt"
    if os.path.exists(output_filename):
        os.remove(output_filename)
    for i, pk_b58 in enumerate(private_keys, 1):
        try:
            keypair = Keypair.from_base58_string(pk_b58)
            wallet_pubkey = keypair.pubkey()
            associated_token_address = get_associated_token_address(wallet_pubkey, token_mint_pubkey)
            account_info = client.get_account_info(associated_token_address).value
            balance = 0.0
            status = " "
            if account_info:
                response = client.get_token_account_balance(associated_token_address)
                token_balance_data = response.value
                decimals = token_balance_data.decimals
                balance = int(token_balance_data.amount) / (10 ** decimals)
                if balance > 0:
                    status = "✅"
                    wallets_with_spl.append(f"PrivateKey: {pk_b58} | Address: {wallet_pubkey} | Balance: {balance} {token_symbol} | Mint: {token_mint_address} | Decimals: {decimals}")
            print(f"[{i}] {status} {wallet_pubkey} : {balance} {token_symbol}")
            time.sleep(0.5)
        except Exception as e:
            print(f"[{i}] ⚠️ Gagal memproses key: {pk_b58[:15]}... | Error: {e}")
    if wallets_with_spl:
        print(f"\n--- Ditemukan {len(wallets_with_spl)} wallet dengan saldo {token_symbol} > 0 ---")
        write_to_file(output_filename, "\n".join(wallets_with_spl))
        print(f"✅ Detail disimpan ke {output_filename}")
    else:
        print(f"\n📭 Tidak ada wallet dengan saldo {token_symbol} yang ditemukan.")

def _perform_solana_send(client: Client, sender_keypair: Keypair, recipient_address: str, amount: float, token_info: dict):
    """Fungsi inti untuk mengirim SOL atau Token SPL, menggunakan metode yang stabil."""
    sender_pubkey = sender_keypair.pubkey()
    try:
        recipient_pubkey = Pubkey.from_string(recipient_address)
        txn = Transaction(recent_blockhash=client.get_latest_blockhash(commitment=Confirmed).value.blockhash)
        txn.fee_payer = sender_pubkey

        if token_info['type'] == 'SOL':
            lamports_to_send = int(amount * 1_000_000_000)
            fee = 5000
            if lamports_to_send > fee:
                lamports_to_send -= fee
            else:
                print("❌ Saldo SOL tidak cukup untuk membayar biaya transaksi.")
                return
            txn.add(transfer(TransferParams(from_pubkey=sender_pubkey, to_pubkey=recipient_pubkey, lamports=lamports_to_send)))

        elif token_info['type'] == 'SPL':
            mint_pubkey = Pubkey.from_string(token_info['mint'])
            decimals = int(token_info['decimals'])
            source_ata = get_associated_token_address(sender_pubkey, mint_pubkey)
            dest_ata = get_associated_token_address(recipient_pubkey, mint_pubkey)
            dest_account_info = client.get_account_info(dest_ata).value
            if dest_account_info is None:
                print(f"ℹ️ Membuat akun token untuk penerima...")
                txn.add(create_associated_token_account(payer=sender_pubkey, owner=recipient_pubkey, mint=mint_pubkey))

            txn.add(spl_transfer(
                SplTransferParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=source_ata,
                    dest=dest_ata,
                    owner=sender_pubkey,
                    amount=int(amount * (10**decimals))
                )
            ))
        
        response = client.send_transaction(txn, sender_keypair)
        tx_signature = response.value
        
        print(f"✅ Transaksi Terkirim! Sejumlah {amount} {token_info['symbol']} ke {recipient_address}")
        print(f"   Verifikasi: {BLOCK_EXPLORER_URLS['solana']}{tx_signature}")

    except Exception as e:
        print(f"❌ Gagal mengirim transaksi dari {sender_pubkey}: {e}")

def send_detected_tokens_solana():
    print("\n=== Kirim Token SOLANA dari Wallet yang Terdeteksi ===")
    solana_files = [f for f in os.listdir(".") if f.startswith("wallet_berisi_") and f.endswith(("_sol.txt", "_solana.txt"))]
    if not solana_files:
        print("❌ Tidak ada file hasil scan Solana ditemukan.")
        return
    print("\nPilih file hasil scan:")
    for idx, fname in enumerate(solana_files, 1): print(f"{idx}. {fname}")
    try:
        choice_idx = int(input("Masukkan nomor pilihan: ")) - 1
        file_to_process = solana_files[choice_idx]
        target_address = input("Masukkan alamat tujuan Solana: ").strip()
        Pubkey.from_string(target_address)
        print(f"\n--- Memproses file: {file_to_process} ---")
        lines = load_lines(file_to_process)
        for line in lines:
            try:
                parts = {k.strip(): v.strip() for k, v in (p.split(':', 1) for p in line.split('|'))}
                pk_b58 = parts['PrivateKey']
                sender_keypair = Keypair.from_base58_string(pk_b58)
                balance_str = parts['Balance'].split()
                amount = float(balance_str[0])
                symbol = balance_str[1]
                
                token_info = {}
                if "sol.txt" in file_to_process:
                    token_info = {'type': 'SOL', 'symbol': 'SOL'}
                else:
                    token_info = {'type': 'SPL', 'symbol': symbol, 'mint': parts['Mint'], 'decimals': parts['Decimals']}
                
                print(f"\nMengirim {amount} {token_info['symbol']} dari {sender_keypair.pubkey()}...")
                _perform_solana_send(solana_client, sender_keypair, target_address, amount, token_info)
                time.sleep(5)
            except Exception as e:
                print(f"⚠️ Gagal memproses baris: '{line}'. Error: {e}")
    except (ValueError, IndexError):
        print("❌ Pilihan atau alamat tidak valid.")
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")

# --- FUNGSI-FUNGSI INTI LAINNYA ---
def cek_semua_rpc():
    print("\n🔌 Mengecek koneksi ke semua jaringan EVM...\n")
    gagal_evm = []
    for name, url in EVM_NETWORKS.items():
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 10}))
            if w3.is_connected(): print(f"🟢 {name.upper():<10} - Terhubung (Block #{w3.eth.block_number})")
            else:
                print(f"🔴 {name.upper():<10} - GAGAL koneksi: RPC tidak merespons.")
                gagal_evm.append(name)
        except Exception as e:
            print(f"🔴 {name.upper():<10} - Error tak terduga: {str(e)}")
            gagal_evm.append(name)
    if not gagal_evm: print("\n✅ Semua RPC EVM aman!")
    else: print(f"\n⚠️ Ada {len(gagal_evm)} jaringan EVM yang gagal terhubung: {', '.join(gagal_evm)}")
    print("\n🔌 Mengecek koneksi ke jaringan TRON & SOLANA...\n")
    try:
        client_tron = Tron()
        _ = client_tron.get_latest_block()
        print("🟢 TRON - Terhubung")
    except Exception as e:
        print(f"🔴 TRON - GAGAL koneksi: {e}")
    try:
        block_height = solana_client.get_block_height().value
        print(f"🟢 SOLANA - Terhubung (Block #{block_height})")
    except Exception as e:
        print(f"🔴 SOLANA - GAGAL koneksi: {e}")
    print("\n")

def scan_custom_token_evm():
    print("\n--- Scan Token Kustom di Jaringan EVM ---")
    for i, (chain, rpc) in enumerate(EVM_NETWORKS.items(), 1): print(f"{i}. {chain.upper()}")
    try:
        idx_choice = int(input("Masukkan nomor jaringan: ")) - 1
        chain_name = list(EVM_NETWORKS.keys())[idx_choice]
        rpc_url = EVM_NETWORKS[chain_name]
    except (ValueError, IndexError):
        print("Input tidak valid.")
        return
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 60}))
    if not w3.is_connected():
        print(f"❌ Gagal koneksi ke jaringan {chain_name}.")
        return
    contract_input = input("Masukkan alamat smart contract token: ").strip()
    try:
        checksum_address = w3.to_checksum_address(contract_input)
        token_contract = w3.eth.contract(address=checksum_address, abi=ERC20_ABI)
        token_name = token_contract.functions.name().call()
        token_decimals = token_contract.functions.decimals().call()
        print(f"\n🪙 Token Ditemukan: {token_name} (decimals: {token_decimals})\n")
    except Exception as e:
        print(f"❌ Gagal membaca kontrak token: {e}")
        return
    print("\nPilih Sumber Data Wallet:\n1. Dari Mnemonic (phrases.txt)\n2. Dari Private Keys (privatekeyevm.txt)")
    source_choice = input("Pilih sumber (1/2): ").strip()
    wallets_for_scan = []
    if source_choice == "1":
        phrases = load_and_clean_phrases()
        if not phrases: return
        for i, phrase in enumerate(phrases):
            try:
                acct = Account.from_mnemonic(phrase)
                wallets_for_scan.append({"address": acct.address, "private_key": "0x" + acct.key.hex(), "index": i + 1})
            except Exception as e: write_to_file(INVALID_MNEMONIC_FILE, f"INVALID MNEMONIC: {phrase} -> {e}")
    elif source_choice == "2":
        keys = load_lines(PRIVATEKEY_EVM_FILE)
        if not keys: return
        for i, pk_hex in enumerate(keys):
            try:
                acct = Account.from_key(pk_hex)
                wallets_for_scan.append({"private_key": pk_hex, "address": acct.address, "index": i + 1})
            except Exception as e: write_to_file(INVALID_MNEMONIC_FILE, f"INVALID EVM KEY: {pk_hex} -> {e}")
    else:
        print("Pilihan tidak valid.")
        return
    if not wallets_for_scan:
        print("Tidak ada wallet yang bisa di-scan.")
        return
    wallets_with_token = []
    output_filename = f"{EVM_OUTPUT_FILE_PREFIX}{token_name.lower().replace(' ', '_')}_{chain_name}.txt"
    if os.path.exists(output_filename):
        os.remove(output_filename)
    print(f"\n🚀 Memulai scan {token_name} untuk {len(wallets_for_scan)} wallet...\n")
    for wallet in wallets_for_scan:
        try:
            balance = token_contract.functions.balanceOf(wallet['address']).call() / (10 ** token_decimals)
            status_indicator = "✅" if balance > 0 else " "
            print(f"[{wallet['index']}] {status_indicator} {wallet['address']} : {balance:.4f} {token_name}")
            if balance > 0: wallets_with_token.append({"private_key": wallet['private_key'], "address": wallet['address'], "balance": balance, "token_name": token_name, "token_contract_address": checksum_address, "token_decimals": token_decimals, "chain": chain_name})
        except Exception as e: print(f"[{wallet['index']}] ⚠️ Gagal memproses wallet {wallet['address']}: {e}")
        time.sleep(1)
    if wallets_with_token:
        print(f"\n--- Ditemukan {len(wallets_with_token)} wallet dengan {token_name} > 0 ---")
        with open(output_filename, "w", encoding='utf-8') as f:
            for data in wallets_with_token: f.write(f"Private Key: {data['private_key']} | Address: {data['address']} | Balance: {data['balance']:.4f} {data['token_name']} | Contract: {data['token_contract_address']} | Decimals: {data['token_decimals']} | Jaringan: {data['chain']}\n")
        print(f"✅ Detail disimpan ke {output_filename}\n")
    else: print("\n📭 Tidak ada wallet dengan token tersebut ditemukan.\n")

def generate_wallet_phrase_evm(count):
    print(f"\nGenerasi {count} mnemonic phrase EVM...")
    with open(PHRASE_FILE, "a", encoding='utf-8') as f:
        for _ in range(count): _, mnemonic = Account.create_with_mnemonic(); f.write(f"{mnemonic}\n")
    print(f"✅ {count} mnemonic EVM telah disimpan ke {PHRASE_FILE}\n")

def generate_wallet_private_key_evm(count):
    print(f"\nGenerasi {count} private key EVM...")
    with open(PRIVATEKEY_EVM_FILE, "a", encoding='utf-8') as f:
        for _ in range(count): acct = Account.create(); f.write(f"{'0x' + acct.key.hex()}\n")
    print(f"✅ {count} private key EVM telah disimpan ke {PRIVATEKEY_EVM_FILE}\n")

def generate_wallet_private_key_tron(count):
    print(f"\nGenerasi {count} private key TRON...")
    with open(PRIVATEKEY_TRON_FILE, "a", encoding='utf-8') as f:
        for _ in range(count): pk = TronPrivateKey(os.urandom(32)); f.write(f"{pk.hex()}\n")
    print(f"✅ {count} private key TRON telah disimpan ke {PRIVATEKEY_TRON_FILE}\n")

def _perform_evm_send(private_key, sender_address, target_address, token_symbol_from_file, _, token_contract_addr, token_decimals, chain_name):
    try:
        rpc_url = EVM_NETWORKS.get(chain_name)
        if not rpc_url: return False
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 60}))
        if not w3.is_connected(): return False
        acct = Account.from_key(private_key)
        contract = w3.eth.contract(address=w3.to_checksum_address(token_contract_addr), abi=ERC20_ABI)
        balance = contract.functions.balanceOf(sender_address).call()
        if balance == 0: return False
        tx_dict = {'from': acct.address, 'nonce': w3.eth.get_transaction_count(acct.address), 'gas': 300000, 'gasPrice': w3.eth.gas_price}
        if chain_name == 'zksync': tx_dict['chainId'] = w3.eth.chain_id
        tx = contract.functions.transfer(w3.to_checksum_address(target_address), balance).build_transaction(tx_dict)
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash_hex = w3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()
        explorer_url = BLOCK_EXPLORER_URLS.get(chain_name, "")
        clickable_url = f"{explorer_url}{tx_hash_hex}" if explorer_url else "N/A"
        print(f"✅ TX sent: {balance / (10**token_decimals):.4f} {token_symbol_from_file} -> {target_address}")
        print(f"   Hash: {tx_hash_hex}\n   Verifikasi: {clickable_url}")
        write_to_file("tx_log.txt", f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] TX_EVM | {chain_name.upper()} | From: {acct.address} | Hash: {tx_hash_hex}")
        return True
    except Exception as e:
        if "insufficient funds" in str(e).lower(): print(f"❌ Gagal: Saldo native tidak cukup untuk gas di {chain_name.upper()}.")
        else: print(f"❌ Gagal kirim {token_symbol_from_file}: {e}")
        return False

def send_detected_tokens_evm():
    print("\n=== Kirim Token EVM dari Wallet yang Terdeteksi ===")
    evm_files = [f for f in os.listdir(".") if f.startswith(EVM_OUTPUT_FILE_PREFIX) and f.endswith(".txt")]
    if not evm_files:
        print("❌ Tidak ada file hasil scan token EVM ditemukan.")
        return
    print("\nPilih file hasil scan:")
    for idx, fname in enumerate(evm_files, 1): print(f"{idx}. {fname}")
    try:
        choice_idx = int(input("Masukkan nomor pilihan: ")) - 1
        file_path = evm_files[choice_idx]
        target_address = input("Masukkan alamat tujuan (EVM): ").strip()
        if not Web3.is_address(target_address):
            print("❌ Alamat tujuan EVM tidak valid.")
            return
        print(f"\n--- Memproses file: {file_path} ---")
        lines = load_lines(file_path)
        for line in lines:
            try:
                parts = {k.strip(): v.strip() for k, v in (p.split(':', 1) for p in line.split('|'))}
                print(f"\nProcessing: {parts['Address']} | {parts['Balance']} ({parts['Jaringan']})...")
                _perform_evm_send(parts['Private Key'], parts['Address'], target_address, parts['Balance'].split()[1], float(parts['Balance'].split()[0]), parts['Contract'], int(parts['Decimals']), parts['Jaringan'].lower())
                time.sleep(3)
            except Exception as e: print(f"⚠️ Gagal memproses baris: '{line}'. Error: {e}")
    except (ValueError, IndexError): print("❌ Pilihan tidak valid.")
    except Exception as e: print(f"Terjadi kesalahan: {e}")

def _private_key_to_tron_address(private_key):
    try:
        return TronPrivateKey(bytes.fromhex(private_key)).public_key.to_base58check_address()
    except Exception: return None

# ==============================================================================
# ===== FUNGSI BARU UNTUK MENU 4 (MULAI) =====
# ==============================================================================

def scan_private_keys_evm_new():
    print("\n[🔍] Memeriksa Private Key EVM dan mendapatkan alamatnya:")
    private_keys = load_lines(PRIVATEKEY_EVM_FILE)
    if not private_keys: return
    with open(ADDR_EVM_OUT, 'w', encoding='utf-8') as f:
        for i, pk_hex in enumerate(private_keys, 1):
            try:
                acct = Account.from_key(pk_hex)
                address = acct.address
                print(f"[{i}] ✅ PrivateKey: {pk_hex[:10]}... | Address: {address}")
                f.write(address + "\n")
            except Exception as e:
                print(f"[{i}] ❌ Private Key EVM tidak valid: {pk_hex[:15]}... | Error: {e}")
    print(f"\n📁 Alamat EVM disimpan ke: {ADDR_EVM_OUT}")

def scan_private_keys_tron_new():
    print("\n[🔍] Memeriksa Private Key TRON dan mendapatkan alamatnya:")
    private_keys = load_lines(PRIVATEKEY_TRON_FILE)
    if not private_keys: return
    with open(ADDR_TRON_OUT, 'w', encoding='utf-8') as f:
        for i, pk_hex in enumerate(private_keys, 1):
            try:
                address = _private_key_to_tron_address(pk_hex)
                if not address:
                    raise ValueError("Gagal menghasilkan alamat dari private key")
                print(f"[{i}] ✅ PrivateKey: {pk_hex[:10]}... | Address: {address}")
                f.write(address + "\n")
            except Exception as e:
                print(f"[{i}] ❌ Private Key TRON tidak valid: {pk_hex[:15]}... | Error: {e}")
    print(f"\n📁 Alamat TRON disimpan ke: {ADDR_TRON_OUT}")

# ==============================================================================
# ===== FUNGSI BARU UNTUK MENU 4 (SELESAI) =====
# ==============================================================================

def scan_tron_stablecoins():
    print("=== CEK SALDO STABLECOIN TRON (VIA TRONSCAN API) ===")
    STABLECOINS_TRON = {"USDT": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "USDC": "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8", "TUSD": "TUpMhErZL4d8Pyb229UoCHcZzgsfG1r2p1"}
    private_keys = load_lines(PRIVATEKEY_TRON_FILE)
    if not private_keys: return
    print(f"\n🚀 Memulai scan untuk {len(private_keys)} wallet...")
    all_found_wallets = []
    for i, priv_key in enumerate(private_keys, start=1):
        address = _private_key_to_tron_address(priv_key)
        if not address:
            print(f"\n[{i}/{len(private_keys)}] ❌ Key tidak valid: {priv_key[:10]}...")
            continue
        print(f"\n[{i}/{len(private_keys)}] Cek Alamat: {address}")
        try:
            url = f"https://apilist.tronscanapi.com/api/accountv2?address={address}"
            data = requests.get(url, timeout=10).json()
            balances_found = {}
            if int(data.get('balance', 0)) / (10**6) > 0.01:
                balances_found['TRX'] = {'balance': int(data.get('balance', 0)) / (10**6), 'contract': 'TRX', 'decimals': 6}
            for token in data.get("trc20token_balances", []):
                symbol, contract_addr = token.get("tokenAbbr", ""), token.get("tokenId", "")
                if symbol in STABLECOINS_TRON and contract_addr == STABLECOINS_TRON[symbol]:
                    balance = int(token.get("balance", "0")) / (10 ** int(token.get("tokenDecimal", 6)))
                    if balance > 0.01:
                        balances_found[symbol] = {"balance": balance, "contract": contract_addr, "decimals": int(token.get("tokenDecimal", 6))}
            if balances_found:
                for symbol, balance_data in balances_found.items():
                    print(f"     ✅ Saldo Ditemukan: {balance_data['balance']:.6f} {symbol}")
                    output_line = f"Private Key: {priv_key} | Address: {address} | Balance: {balance_data['balance']:.4f} {symbol} | Contract: {balance_data['contract']} | Decimals: {balance_data['decimals']} | Jaringan: tron"
                    write_to_file(f"wallet_berisi_{symbol.lower()}_tron.txt", output_line)
                all_found_wallets.append(address)
            else: print("     - Tidak ada saldo yang terdeteksi.")
        except Exception as e:
            print(f"     [!] Error saat memproses alamat: {e}")
        time.sleep(1)
    print("\n\n--- Proses Scan TRON Selesai ---")
    if not all_found_wallets: print("📭 Tidak ada wallet dengan saldo stablecoin yang terdeteksi.")
    else: print(f"✅ Berhasil menemukan dan menyimpan saldo dari {len(all_found_wallets)} wallet.")

# --- Menu Utama Aplikasi ---
def main_menu():
    while True:
        print("\n" + "="*30 + "\n=== APLIKASI SCAN & TRANSFER WALLET ===\n" + "="*30)
        print("0. Tes semua koneksi jaringan")
        print("1. Scan Saldo Token (EVM & Solana)")
        print("2. Kirim Token dari Wallet Terdeteksi")
        print("3. Generate wallet baru")
        print("4. Cek Alamat Wallet (Private Key)")
        print("5. Scan Saldo Stablecoin TRON")
        print("6. Validasi & Bersihkan mnemonic")
        print("7. Keluar")
        print("="*30)
        pilihan = input("Pilih menu: ").strip()
        print("\n")

        if pilihan == "0":
            cek_semua_rpc()
        elif pilihan == "1":
            print("\n--- Menu Scan Saldo Token ---\n1. EVM (Scan Token Kustom)\n2. Solana")
            jaringan_choice = input("Pilih Jaringan (1/2): ").strip()
            if jaringan_choice == '1': scan_custom_token_evm()
            elif jaringan_choice == '2':
                while True:
                    print("\n--- Menu Scan Solana ---\n1. Cek Wallet Tunggal\n2. Scan Massal dari File\n0. Kembali")
                    sol_scan_choice = input("Pilihan: ").strip()
                    if sol_scan_choice == '1':
                        address = input("Masukkan alamat wallet Solana: ")
                        cek_saldo_sol(solana_client, address)
                    elif sol_scan_choice == '2':
                        print("\n--- Menu Scan Massal Solana ---\n1. Scan Saldo SOL\n2. Scan Saldo Token SPL\n0. Kembali")
                        mass_choice = input("Pilihan: ").strip()
                        if mass_choice == '1': scan_sol_balance_massal(solana_client)
                        elif mass_choice == '2': scan_spl_token_massal(solana_client)
                        elif mass_choice == '0': continue
                    elif sol_scan_choice == '0': break
        elif pilihan == "2":
            print("\n--- Menu Kirim Token Terdeteksi ---\n1. Kirim EVM\n2. Kirim Solana")
            send_choice = input("Pilih Jaringan (1/2): ").strip()
            if send_choice == '1': send_detected_tokens_evm()
            elif send_choice == '2': send_detected_tokens_solana()
        elif pilihan == "3":
            print("\n--- Generate Wallet Baru ---\n1. Mnemonic (EVM)\n2. Private Key (EVM)\n3. Private Key (TRON)\n4. Private Key (Solana)")
            gen_choice = input("Pilihan: ").strip()
            try:
                jumlah = int(input("Jumlah yang ingin digenerate: "))
                if gen_choice == '1': generate_wallet_phrase_evm(jumlah)
                elif gen_choice == '2': generate_wallet_private_key_evm(jumlah)
                elif gen_choice == '3': generate_wallet_private_key_tron(jumlah)
                elif gen_choice == '4': generate_wallet_private_key_sol(jumlah)
            except ValueError: print("Jumlah harus angka.")
        elif pilihan == "4":
            print("\n--- Cek Alamat dari Private Key ---\n1. Private Key (EVM)\n2. Private Key (TRON)\n3. Private Key (Solana)")
            check_choice = input("Pilih jenis (1-3): ").strip()
            # ===== BAGIAN YANG DIPERBAIKI =====
            if check_choice == '1':
                scan_private_keys_evm_new()
            elif check_choice == '2':
                scan_private_keys_tron_new()
            elif check_choice == '3':
                scan_private_keys_sol_new()
            # =================================
        elif pilihan == "5":
            scan_tron_stablecoins()
        elif pilihan == "6":
            load_and_clean_phrases(show_detail=True)
        elif pilihan == "7":
            print("Terima kasih!")
            sys.exit()
        else:
            print("Pilihan tidak valid.")

if __name__ == "__main__":
    main_menu()
