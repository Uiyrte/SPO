using System;
using System.Collections.Generic;
using System.Linq;

namespace Demo
{
    public abstract class ShapeBase
    {
        public abstract double Area { get; }
        public virtual string Describe() => $"Площадь {Area:F2}";
    }

    public class Circle : ShapeBase
    {
        public double Radius { get; set; }

        public Circle(double radius)
        {
            Radius = radius;
        }

        public override double Area => Math.PI * Radius * Radius;
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

    public static class Program
    {
        public static void Main()
        {
            var shapes = new List<ShapeBase>();
            shapes.Add(new Circle(2.5));
            shapes.Add(new Circle(1.0));
            shapes.Add(new Rectangle(3.0, 4.0)); 

            var bigShapes = shapes
                .Where(s => s.Area > 2.0)
                .OrderByDescending(s => s.Area);

            foreach (var shape in bigShapes)
            {
                Console.WriteLine(shape.Describe());
            }

            string label = shapes.Count switch
            {
                0 => "пусто",
                1 => "одна фигура",
                _ when shapes.Count > 5 => "много",
                _ => "несколько",
            };

            try
            {

                if (shapes.Count > 0 && shapes[0] is Circle c)
                {
                    Console.WriteLine($"Первая — круг r={c.Radius}");
                }
                else if (shapes.Count > 2 && shapes[2] is Rectangle r)
                {
                    Console.WriteLine($"Третья — прямоугольник {r.Width}x{r.Height}");
                }
            }
            catch (Exception ex) when (ex.Message.Length > 0)
            {
                Console.WriteLine($"Ошибка: {ex.Message}");
            }
            finally
            {
                Console.WriteLine($"Итог: {label}");
            }
        }
    }
}
