public class LuhnValidator {
    public static boolean isValid(String cardNumber) {
        if (cardNumber == null || cardNumber.isBlank()) {
            return false;
        }
        String normalized = cardNumber.replace(" ", "");
        if (!normalized.chars().allMatch(Character::isDigit)) {
            return false;
        }

        int checksum = 0;
        boolean shouldDouble = false;
        for (int i = normalized.length() - 1; i >= 0; i--) {
            int digit = Character.getNumericValue(normalized.charAt(i));
            checksum += shouldDouble ? fold(digit * 2) : digit;
            shouldDouble = !shouldDouble;
        }
        return checksum % 10 == 0;
    }

    private static int fold(int value) {
        return value > 9 ? value - 9 : value;
    }
}
