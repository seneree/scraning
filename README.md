
# Aplikasi Scan & Transfer Wallet (EVM, Solana, TRON)

## ✨ Fitur Utama
- Scan saldo token EVM (token custom, ERC-20)
- Scan saldo Solana (SOL dan token SPL)
- Scan stablecoin TRON (USDT, USDC, TUSD)
- Generate wallet baru (mnemonic & private key)
- Kirim token dari wallet yang memiliki saldo
- Validasi & pembersihan mnemonic
- Deteksi alamat dari private key semua chain

## 📁 Struktur File
- phrases.txt - Mnemonic untuk EVM
- privatekeyevm.txt - Private Key EVM
- privatekeytron.txt - Private Key TRON
- privatekeysol.txt - Private Key Solana
- addresevm.txt, addrestron.txt, addressol.txt - Alamat hasil scan
- wallet_berisi_*.txt - Hasil scan wallet dengan saldo

## 📦 Dependensi yang Dibutuhkan
Install semua dependensi dengan perintah berikut:

```bash
pip install requests web3 eth-account tronpy mnemonic bip44 solana solders spl-token
```

## 🚀 Cara Menjalankan
Jalankan script dengan Python:

```bash
python scraning.py
```

## 🧩 Menu Aplikasi
0. Tes semua koneksi jaringan
1. Scan Saldo Token (EVM & Solana)
2. Kirim Token dari Wallet Terdeteksi
3. Generate wallet baru
4. Cek Alamat Wallet (Private Key)
5. Scan Saldo Stablecoin TRON
6. Validasi & Bersihkan mnemonic
7. Keluar

### Keterangan Menu:
- Menu 1:
  - Scan token custom (input contract) dari EVM
  - Scan saldo SOL atau SPL token dari wallet Solana
- Menu 2:
  - Kirim semua token yang ditemukan (EVM & Solana)
- Menu 3:
  - Generate mnemonic atau private key untuk EVM, TRON, atau Solana
- Menu 4:
  - Deteksi alamat dari private key
- Menu 5:
  - Cek USDT/USDC/TUSD di jaringan TRON
- Menu 6:
  - Validasi dan sortir mnemonic tidak valid

⚠️ Peringatan Penting
Skrip ini berinteraksi langsung dengan private key Anda. Pastikan Anda menggunakannya di lingkungan yang aman.

Risiko ditanggung oleh pengguna. Kami tidak bertanggung jawab atas kehilangan aset apa pun yang mungkin terjadi akibat penggunaan skrip ini. Selalu uji coba dengan wallet yang tidak memiliki aset signifikan.
