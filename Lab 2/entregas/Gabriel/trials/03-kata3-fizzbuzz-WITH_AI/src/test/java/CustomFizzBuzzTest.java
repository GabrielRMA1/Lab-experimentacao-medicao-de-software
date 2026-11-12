import org.junit.jupiter.api.Test;
import java.util.LinkedHashMap;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

public class CustomFizzBuzzTest {
    @Test void testCustomRules() {
        Map<Integer, String> rules = new LinkedHashMap<>();
        rules.put(3, "Foo");
        rules.put(5, "Bar");

        assertEquals("Foo", CustomFizzBuzz.evaluate(3, rules));
        assertEquals("Bar", CustomFizzBuzz.evaluate(5, rules));
        assertEquals("FooBar", CustomFizzBuzz.evaluate(15, rules));
        assertEquals("7", CustomFizzBuzz.evaluate(7, rules));
    }
}
