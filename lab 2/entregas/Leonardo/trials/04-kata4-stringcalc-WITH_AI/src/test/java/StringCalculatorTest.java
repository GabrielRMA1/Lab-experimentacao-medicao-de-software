import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class StringCalculatorTest {
    @Test void testEmptyString() { assertEquals(0, StringCalculator.add("")); }
    @Test void testSingleNumber() { assertEquals(1, StringCalculator.add("1")); }
    @Test void testTwoNumbers() { assertEquals(6, StringCalculator.add("1,5")); }
    @Test void testCustomDelimiter() { assertEquals(3, StringCalculator.add("//;\n1;2")); }
    @Test void testNegativeNumbersException() {
        assertThrows(IllegalArgumentException.class, () -> StringCalculator.add("1,-2,3"));
    }
}
