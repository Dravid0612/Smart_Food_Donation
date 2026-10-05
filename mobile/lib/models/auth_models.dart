/// The four account roles. Admin accounts are never created through the
/// public registration screen — they're provisioned internally, so
/// [UserRole.admin] only ever appears as a login outcome, never as a
/// registration option.
enum UserRole { donor, ngo, volunteer, admin }

/// Result of a successful login or registration call.
///
/// [ngoVerified] only matters when [role] is [UserRole.ngo]: an NGO that
/// hasn't been approved by an admin yet must be routed to the
/// verification-pending screen instead of the normal NGO dashboard.
class AuthResult {
  final UserRole role;
  final String displayName;
  final bool ngoVerified;

  const AuthResult({
    required this.role,
    required this.displayName,
    this.ngoVerified = true,
  });
}

/// Thrown by the injected auth callbacks on failure. [message] must
/// already be plain-language and safe to show directly to the user (e.g.
/// "Invalid credentials", never a raw HTTP status or stack trace).
class AuthException implements Exception {
  final String message;
  const AuthException(this.message);

  @override
  String toString() => message;
}
