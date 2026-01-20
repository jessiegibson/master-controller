# Encryption Implementation

**Module**: `src/encryption/`
**Date**: 2024-12-28
**Status**: Implementation Complete

## Files Created

| File | Purpose |
|------|---------|
| `mod.rs` | Module exports and re-exports |
| `key.rs` | Argon2id key derivation with HKDF domain separation |
| `cipher.rs` | AES-256-GCM encryption/decryption |
| `recovery.rs` | BIP39 mnemonic generation and validation |
| `secure_memory.rs` | Secure memory types with zeroization |
| `file.rs` | Encrypted file I/O operations |
| `error.rs` | Encryption-specific error types |

## Cryptographic Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| KDF | Argon2id | Memory-hard, OWASP recommended |
| Memory | 64 MB | Balance security/performance |
| Iterations | 3 | OWASP minimum |
| Parallelism | 4 | Multi-core optimization |
| Salt | 16 bytes random | Prevent rainbow tables |
| Cipher | AES-256-GCM | Authenticated encryption |
| Nonce | 12 bytes random | GCM recommended size |
| Key size | 256 bits | Maximum AES security |
| Domain separation | HKDF-SHA256 | Cryptographically separate keys |

## File Format

```
[FINCRYPT][version:1][salt:16][nonce:12][ciphertext+tag...]
```

---

## src/encryption/mod.rs

```rust
//! Encryption module for the Finance CLI.
//!
//! This module provides comprehensive cryptographic functionality for protecting
//! financial data at rest. All sensitive data is encrypted using AES-256-GCM
//! with keys derived from user passwords via Argon2id.
//!
//! # Architecture
//!
//! ```text
//! User Password/Recovery Phrase
//!         │
//!         ▼
//! ┌─────────────────────────────────────────────────────────────┐
//! │                  Argon2id Key Derivation                     │
//! │  Memory: 64MB, Iterations: 3, Parallelism: 4               │
//! └─────────────────────────────────────────────────────────────┘
//!         │
//!         ▼
//! ┌─────────────────────────────────────────────────────────────┐
//! │                 Master Key (256-bit)                        │
//! │                 (Memory only, never stored)                 │
//! └─────────────────────────────────────────────────────────────┘
//!         │
//!         ├── HKDF-SHA256("database") ──► Database Encryption Key
//!         ├── HKDF-SHA256("config")   ──► Config Encryption Key  
//!         └── HKDF-SHA256("backup")   ──► Backup Encryption Key
//!                          │
//!                          ▼
//! ┌─────────────────────────────────────────────────────────────┐
//! │                  AES-256-GCM Encryption                     │
//! │  Nonce: 12 bytes random, Tag: 16 bytes authentication      │
//! └─────────────────────────────────────────────────────────────┘
//! ```
//!
//! # Security Properties
//!
//! - **Confidentiality**: AES-256 encryption protects data contents
//! - **Integrity**: GCM authentication detects tampering
//! - **Forward Secrecy**: Keys zeroized immediately after use
//! - **Memory Safety**: All sensitive data uses secure memory types
//! - **Domain Separation**: Different keys for database/config/backup
//! - **Recovery**: BIP39 mnemonic enables password-independent recovery
//!
//! # Usage
//!
//! ```rust
//! use finance_cli::encryption::{MasterKey, FileEncryption, SecureString};
//!
//! // Derive master key from password
//! let password = SecureString::new("user_password".to_string());
//! let master_key = MasterKey::derive_from_password(password)?;
//!
//! // Create domain-specific encryption key
//! let db_key = master_key.derive_database_key()?;
//!
//! // Encrypt a file
//! let file_enc = FileEncryption::new();
//! file_enc.encrypt_file(
//!     Path::new("plaintext.db"),
//!     Path::new("encrypted.db"),
//!     &db_key,
//! )?;
//! ```

pub mod cipher;
pub mod error;
pub mod file;
pub mod key;
pub mod recovery;
pub mod secure_memory;

// Re-export commonly used types
pub use cipher::{Cipher, EncryptedData, EncryptionNonce};
pub use error::{Error, Result};
pub use file::{EncryptedFileHeader, FileEncryption};
pub use key::{DerivedKey, KeyDerivation, KeyDerivationParams, MasterKey, Salt};
pub use recovery::{RecoveryPhrase, BIP39_WORD_COUNT};
pub use secure_memory::{
    SecureBuffer, SecureBytes, SecureString, secure_string_from_input,
    mlock_if_available, secure_delete,
};

/// Current encryption format version.
///
/// This version is embedded in encrypted files to enable future format migrations.
/// Version 1 uses:
/// - Argon2id key derivation
/// - AES-256-GCM encryption
/// - HKDF-SHA256 domain separation
/// - BIP39 recovery phrases
pub const ENCRYPTION_VERSION: u8 = 1;

/// Magic bytes for encrypted file identification.
///
/// These bytes appear at the start of all encrypted files to:
/// - Identify files as encrypted by this application
/// - Prevent accidental processing of non-encrypted files
/// - Enable format detection and validation
pub const MAGIC_BYTES: &[u8; 8] = b"FINCRYPT";

/// Initialize the encryption subsystem.
///
/// This function should be called once at application startup to:
/// - Verify cryptographic library availability
/// - Initialize secure random number generation
/// - Set up memory protection where available
///
/// # Errors
///
/// Returns an error if:
/// - Cryptographic libraries are unavailable
/// - Random number generation fails
/// - Memory protection setup fails
///
/// # Example
///
/// ```rust
/// use finance_cli::encryption;
///
/// // Initialize encryption at application startup
/// encryption::init()?;
/// ```
pub fn init() -> Result<()> {
    // Verify that we can generate random bytes
    let mut test_bytes = [0u8; 32];
    use rand::RngCore;
    rand::thread_rng().fill_bytes(&mut test_bytes);
    
    // Verify all bytes are not zero (extremely unlikely if RNG works)
    if test_bytes.iter().all(|&b| b == 0) {
        return Err(Error::Initialization(
            "Random number generator appears to be non-functional".into()
        ));
    }

    // Initialize memory protection
    secure_memory::init_memory_protection()?;

    tracing::info!("Encryption subsystem initialized successfully");
    Ok(())
}

/// Cleanup the encryption subsystem.
///
/// This function should be called at application shutdown to:
/// - Zeroize any remaining sensitive data
/// - Release memory protection resources
/// - Perform final security cleanup
///
/// This is automatically called by the application's cleanup handlers,
/// but can be called explicitly if needed.
pub fn cleanup() {
    secure_memory::cleanup_memory_protection();
    tracing::info!("Encryption subsystem cleanup completed");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_init_and_cleanup() {
        // Test that init and cleanup work without errors
        init().expect("Encryption init should succeed");
        cleanup(); // Should not panic
    }

    #[test]
    fn test_magic_bytes_constant() {
        assert_eq!(MAGIC_BYTES, b"FINCRYPT");
        assert_eq!(MAGIC_BYTES.len(), 8);
    }

    #[test]
    fn test_encryption_version() {
        assert_eq!(ENCRYPTION_VERSION, 1);
    }
}
```

---

## src/encryption/error.rs

```rust
//! Encryption-specific error types.
//!
//! This module defines all error conditions that can occur during cryptographic
//! operations. Errors are designed to be informative for debugging while
//! avoiding leakage of sensitive information.

use std::fmt;

/// Encryption operation errors.
///
/// All error messages are carefully crafted to avoid leaking sensitive
/// information while providing enough detail for debugging and user feedback.
#[derive(Debug)]
pub enum Error {
    /// Key derivation failed.
    ///
    /// This can occur due to:
    /// - Invalid Argon2id parameters
    /// - Insufficient memory for key derivation
    /// - Corrupted salt data
    KeyDerivation(String),

    /// Encryption operation failed.
    ///
    /// This typically indicates:
    /// - Invalid key material
    /// - Corrupted cipher state
    /// - Memory allocation failure
    Encryption(String),

    /// Decryption failed.
    ///
    /// This can indicate:
    /// - Wrong password/key
    /// - Corrupted ciphertext
    /// - Authentication tag mismatch
    /// - Invalid nonce/IV
    Decryption(String),

    /// BIP39 mnemonic operation failed.
    ///
    /// This occurs when:
    /// - Invalid word in mnemonic phrase
    /// - Incorrect phrase length
    /// - Checksum validation failure
    /// - Entropy generation failure
    Mnemonic(String),

    /// File I/O operation failed.
    ///
    /// Includes the path for debugging while avoiding sensitive data exposure.
    Io {
        /// The file path that caused the error (if safe to expose)
        path: std::path::PathBuf,
        /// The underlying I/O error
        source: std::io::Error,
    },

    /// Memory protection operation failed.
    ///
    /// This can occur when:
    /// - mlock() system call fails
    /// - Insufficient memory lock privileges
    /// - Memory allocation failure
    /// - Platform doesn't support memory protection
    MemoryProtection(String),

    /// Invalid parameter provided to encryption function.
    ///
    /// This indicates programming errors such as:
    /// - Zero-length keys
    /// - Invalid nonce sizes
    /// - Malformed encrypted data
    InvalidParameter(String),

    /// Initialization of encryption subsystem failed.
    ///
    /// This can occur when:
    /// - Cryptographic libraries are unavailable
    /// - Hardware random number generator fails
    /// - System security features are disabled
    Initialization(String),

    /// File format version not supported.
    ///
    /// This occurs when trying to decrypt files created with:
    /// - Future versions of the application
    /// - Corrupted version headers
    /// - Non-encrypted files mistaken for encrypted ones
    UnsupportedVersion {
        /// The version found in the file
        found: u8,
        /// The maximum version supported by this implementation
        supported: u8,
    },
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::KeyDerivation(msg) => {
                write!(f, "Key derivation failed: {}", msg)
            }
            Self::Encryption(msg) => {
                write!(f, "Encryption failed: {}", msg)
            }
            Self::Decryption(msg) => {
                write!(f, "Decryption failed: {}", msg)
            }
            Self::Mnemonic(msg) => {
                write!(f, "Recovery phrase error: {}", msg)
            }
            Self::Io { path, source } => {
                write!(f, "File operation failed for {}: {}", path.display(), source)
            }
            Self::MemoryProtection(msg) => {
                write!(f, "Memory protection error: {}", msg)
            }
            Self::InvalidParameter(msg) => {
                write!(f, "Invalid parameter: {}", msg)
            }
            Self::Initialization(msg) => {
                write!(f, "Encryption initialization failed: {}", msg)
            }
            Self::UnsupportedVersion { found, supported } => {
                write!(
                    f,
                    "Unsupported encryption version {} (maximum supported: {})",
                    found, supported
                )
            }
        }
    }
}

impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io { source, .. } => Some(source),
            _ => None,
        }
    }
}

// Conversion from standard I/O errors
impl From<std::io::Error> for Error {
    fn from(err: std::io::Error) -> Self {
        Self::Io {
            path: std::path::PathBuf::from("<unknown>"),
            source: err,
        }
    }
}

/// Result type for encryption operations.
pub type Result<T> = std::result::Result<T, Error>;

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_error_display() {
        let err = Error::KeyDerivation("test error".into());
        assert_eq!(err.to_string(), "Key derivation failed: test error");

        let err = Error::UnsupportedVersion { found: 2, supported: 1 };
        assert_eq!(
            err.to_string(),
            "Unsupported encryption version 2 (maximum supported: 1)"
        );
    }

    #[test]
    fn test_io_error_conversion() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let enc_err = Error::from(io_err);
        
        match enc_err {
            Error::Io { path, source } => {
                assert_eq!(path, PathBuf::from("<unknown>"));
                assert_eq!(source.kind(), std::io::ErrorKind::NotFound);
            }
            _ => panic!("Expected Io error variant"),
        }
    }
}
```

---

## src/encryption/secure_memory.rs

```rust
//! Secure memory handling with automatic zeroization.
//!
//! This module provides secure memory types that automatically zeroize their
//! contents when dropped, preventing sensitive data from remaining in memory
//! after use. It also provides memory protection features where supported
//! by the operating system.
//!
//! # Memory Protection
//!
//! On supported platforms, sensitive memory pages can be:
//! - Locked in RAM (prevented from swapping to disk)
//! - Marked as non-readable by debuggers
//! - Protected from core dumps
//!
//! # Zeroization
//!
//! All secure memory types use the `zeroize` crate to ensure that sensitive
//! data is cryptographically erased when no longer needed. This helps prevent:
//! - Memory dump analysis
//! - Swap file examination
//! - Cold boot attacks
//! - Accidental data exposure

use crate::encryption::{Error, Result};
use std::ops::{Deref, DerefMut};
use std::path::Path;
use zeroize::{Zeroize, Zeroizing};

/// Secure string that automatically zeroizes on drop.
///
/// This type wraps a `String` and ensures it is zeroized when no longer needed.
/// Use this for passwords, passphrases, and other sensitive text data.
///
/// # Example
///
/// ```rust
/// use finance_cli::encryption::SecureString;
///
/// let password = SecureString::new("my_secret_password".to_string());
/// // password is automatically zeroized when it goes out of scope
///