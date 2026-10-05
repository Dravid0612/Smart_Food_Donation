import 'package:flutter_test/flutter_test.dart';
import 'package:smart_food_waste_donation/models/auth_models.dart';

void main() {
  group('Auth Models Exact Specification Tests', () {
    test('UserRole enum has exactly the four account roles', () {
      expect(UserRole.values.length, 4);
      expect(UserRole.values, contains(UserRole.donor));
      expect(UserRole.values, contains(UserRole.ngo));
      expect(UserRole.values, contains(UserRole.volunteer));
      expect(UserRole.values, contains(UserRole.admin));
    });

    test('AuthResult instantiates with required and default parameters', () {
      // Default ngoVerified is true
      const resultDonor = AuthResult(
        role: UserRole.donor,
        displayName: 'Heritage Kitchen',
      );
      expect(resultDonor.role, UserRole.donor);
      expect(resultDonor.displayName, 'Heritage Kitchen');
      expect(resultDonor.ngoVerified, isTrue);

      // NGO pending verification
      const resultNgoPending = AuthResult(
        role: UserRole.ngo,
        displayName: 'Hope Shelter',
        ngoVerified: false,
      );
      expect(resultNgoPending.role, UserRole.ngo);
      expect(resultNgoPending.displayName, 'Hope Shelter');
      expect(resultNgoPending.ngoVerified, isFalse);

      // Volunteer result
      const resultVolunteer = AuthResult(
        role: UserRole.volunteer,
        displayName: 'Courier Anita',
      );
      expect(resultVolunteer.role, UserRole.volunteer);
      expect(resultVolunteer.displayName, 'Courier Anita');
      expect(resultVolunteer.ngoVerified, isTrue);

      // Admin result
      const resultAdmin = AuthResult(
        role: UserRole.admin,
        displayName: 'Ops Coordinator',
      );
      expect(resultAdmin.role, UserRole.admin);
      expect(resultAdmin.displayName, 'Ops Coordinator');
    });

    test('AuthException stores message and toString returns message', () {
      const ex = AuthException('Invalid credentials');
      expect(ex.message, 'Invalid credentials');
      expect(ex.toString(), 'Invalid credentials');
      expect(ex, isA<Exception>());
    });
  });
}
