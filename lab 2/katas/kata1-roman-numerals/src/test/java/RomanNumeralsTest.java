import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class RomanNumeralsTest {
    @Test void testSingleDigits() {
        assertEquals("I", RomanNumerals.convert(1));
        assertEquals("IV", RomanNumerals.convert(4));
        assertEquals("IX", RomanNumerals.convert(9));
    }
    @Test void testComplexNumbers() {
        assertEquals("LVIII", RomanNumerals.convert(58));
        assertEquals("MCMXCIV", RomanNumerals.convert(1994));
    }
}