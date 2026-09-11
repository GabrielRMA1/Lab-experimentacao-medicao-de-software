import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class LuhnValidatorTest {
    @Test void testValidCards() {
        assertTrue(LuhnValidator.isValid("49927398716"));
        assertTrue(LuhnValidator.isValid("79927398713"));
    }
    @Test void testInvalidCards() {
        assertFalse(LuhnValidator.isValid("49927398717"));
    }
}