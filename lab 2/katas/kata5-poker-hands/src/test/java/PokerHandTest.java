import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class PokerHandTest {
    @Test void testPair() {
        String[] hand = {"2H", "2D", "5S", "9C", "KD"};
        assertEquals("Pair", PokerHand.evaluate(hand));
    }
    @Test void testFlush() {
        String[] hand = {"2H", "4H", "8H", "10H", "KH"};
        assertEquals("Flush", PokerHand.evaluate(hand));
    }
}