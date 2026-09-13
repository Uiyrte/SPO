using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace Demo
{
    public enum Color { Red, Green, Blue }

    public struct Point
    {
        public double X;
        public double Y;

        public Point(double x, double y)
        {
            X = x;
            Y = y;
        }
    }

    public delegate void Notify(string message);

    public interface IShape
    {
        double Area { get; }
        string Describe();
    }

    public abstract class ShapeBase : IShape
    {
        public event Notify OnCreated;

        protected ShapeBase()
        {
            OnCreated?.Invoke("Создана фигура");
        }

        public abstract double Area { get; }

        public virtual string Describe() => $"Фигура с площадью {Area:F2}";
    }

    public class Circle : ShapeBase
    {
        public double Radius { get; set; }

        public Circle(double radius)
        {
            Radius = radius;
        }

        public override double Area => Math.PI * Radius * Radius;

        public override string ToString() => $"Circle(r={Radius})";
    }

    public class Rectangle : ShapeBase
    {
        public double Width { get; set; }
        public double Height { get; set; }

        public Rectangle(double width, double height)
        {
            Width = width;
            Height = height;
        }

        public override double Area => Width * Height;
    }

    public class ShapeCollection
    {
        private readonly List<IShape> _shapes = new List<IShape>();

        public int Count => _shapes.Count;

        public IShape this[int index]
        {
            get { return _shapes[index]; }
            set { _shapes[index] = value; }
        }

        public void Add(IShape shape)
        {
            _shapes.Add(shape);
        }

        public IEnumerable<IShape> BigShapes(double threshold)
        {
            return _shapes.Where(s => s.Area > threshold).OrderByDescending(s => s.Area);
        }

        public IEnumerable<IShape> QueryBig(double threshold)
        {
            var query =
                from s in _shapes
                where s.Area > threshold
                orderby s.Area descending
                select s;
            return query;
        }
    }

    public record ShapeSummary(string Name, double TotalArea);

    public static class Program
    {
        public static async Task Main(string[] args)
        {
            var shapes = new ShapeCollection();
            shapes.Add(new Circle(1.0));
            shapes.Add(new Circle(2.5));
            shapes.Add(new Rectangle(3.0, 4.0));

            int total = 0;
            for (int i = 0; i < shapes.Count; i++)
            {
                total += i;
            }

            int guard = 0;
            do
            {
                guard++;
            }
            while (guard < 3);

            foreach (var shape in shapes.BigShapes(3.0))
            {
                Console.WriteLine(shape.Describe());
            }

            (double min, double max) bounds = (0.0, 100.0);

            double? nullableArea = null;
            double effectiveArea = nullableArea ?? 0.0;

            string label = shapes.Count switch
            {
                0 => "пусто",
                1 => "одна фигура",
                _ when shapes.Count > 5 => "много",
                _ => "несколько",
            };

            try
            {
                if (shapes.Count > 0 && effectiveArea >= 0)
                {
                    var first = shapes[0];
                    Console.WriteLine(first is Circle c ? $"Первая — круг r={c.Radius}" : "Первая — не круг");
                }

                await Task.Delay(1);
            }
            catch (Exception ex) when (ex.Message.Length > 0)
            {
                Console.WriteLine($"Ошибка: {ex.Message}");
            }
            finally
            {
                Console.WriteLine("Готово");
            }

            using (var scope = new System.IO.MemoryStream())
            {
                scope.WriteByte(1);
            }

            Func<int, int, int> add = (a, b) => a + b;
            int sum = add(2, 3);

            Console.WriteLine($"total={total}, guard={guard}, sum={sum}, label={label}, bounds={bounds.min}-{bounds.max}");
        }
    }
}
