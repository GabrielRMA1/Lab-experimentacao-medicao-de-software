import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class BowlingGameTest {
    @Test void testGutterGame() {
        BowlingGame g = new BowlingGame();
        for (int i = 0; i < 20; i++) g.roll(0);
        assertEquals(0, g.score());
    }
    @Test void testAllOnes() {
        BowlingGame g = new BowlingGame();
        for (int i = 0; i < 20; i++) g.roll(1);
        assertEquals(20, g.score());
    }
    @Test void testOneSpare() {
        BowlingGame g = new BowlingGame();
        g.roll(5); g.roll(5); // Spare
        g.roll(3);
        for (int i = 0; i < 17; i++) g.roll(0);
        assertEquals(16, g.score());
    }
}