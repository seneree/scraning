# 🧠 Scraning – Wallet Scanner EVM & TRON

Script Python berbasis menu CLI untuk mengelola, memindai, dan memvalidasi wallet blockchain. Mendukung jaringan **EVM (Ethereum, Sepolia, Holesky, dll)** dan **TRON**. Dirancang untuk para pemburu airdrop, developer, maupun untuk audit wallet testnet.

---

## ✨ Fitur

- 🔍 Scan token kustom menggunakan smart contract (EVM).
- 💸 Kirim token dari wallet yang terdeteksi (khusus EVM).
- 🧠 Generate wallet baru (berdasarkan *mnemonic phrase* atau *private key*).
- 💰 Cek saldo stablecoin di jaringan TRON.
- 🧹 Validasi dan bersihkan *mnemonic* yang tidak valid dari file.
- 🌐 Tes koneksi ke semua RPC (EVM & TRON).
- 📋 Menu interaktif yang simpel dan ringan.

---

## 📦 File yang Dibutuhkan

| File                 | Fungsi                                     |
| -------------------- | ------------------------------------------ |
| `scraning.py`        | Script utama aplikasi.                     |
| `phrases.txt`        | Daftar *mnemonic phrase* untuk wallet.     |
| `privatekeyevm.txt`  | Daftar *private key* wallet EVM (opsional).|
| `privatekeytron.txt` | Daftar *private key* wallet TRON (opsional).|
| `requirements.txt`   | Daftar pustaka Python yang dibutuhkan.     |

---

## ⚙️ Cara Install & Menjalankan

### 1. Prasyarat
- **Python 3.8+**
- **Koneksi Internet**

### 2. Instalasi & Konfigurasi
Buka terminal atau Command Prompt di folder proyek Anda.

**a. Install semua pustaka yang dibutuhkan dengan perintah:**
```bash
pip install requests web3 eth-account tronpy mnemonic bip44

Konfigurasi Kunci API (Wajib untuk Fitur TRON)
Buka file scraning.py, cari variabel TRONGRID_API_KEY, dan ganti dengan kunci API Trongrid milik Anda.


Menjalankan Skrip
Setelah instalasi selesai, jalankan skrip utama dengan perintah:
```bash

python scraning.py

#### Menu interaktif akan muncul di terminal Anda, seperti contoh di bawah ini:
```text
0. Tes semua koneksi jaringan (RPC EVM & TRON)
1. Scan token kustom menggunakan smart contract (EVM)
2. Kirim token dari wallet yang terdeteksi (EVM only)
3. Generate wallet baru
4. Cek alamat wallet (Private Key / Mnemonic)
5. Scan saldo stablecoin TRON
6. Validasi & bersihkan mnemonic phrases dari file
7. Keluar

## 🧪 Contoh

#### Contoh Output Hasil Scan:
```text
[+] Wallet 0xabc123... memiliki: 0.034 ETH, 15.2 USDT
[+] Wallet TVkXyz... memiliki: 1.5 USDT, 52 TRX
[✔] RPC EVM aktif | RPC TRON aktif
[!] 2 phrasa tidak valid ditemukan dan dihapus

- Jangan pernah membagikan file `phrases.txt` atau `privatekey.txt` Anda.
- Jangan pernah mengunggah file yang berisi kunci privat atau mnemonic phrase ke repositori GitHub publik.
