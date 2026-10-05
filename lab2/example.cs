using System;
using System.Collections.Generic;

namespace GilbMetricAnalysis
{
    class Program
    {
        static void Main(string[] args)
        {
            int n = 10;
            int totalSum = 0;
            List<int> numbers = new List<int>();

            for (int i = 0; i < n; i++)
            {
                numbers.Add(i * 2);
            }

            if (numbers.Count > 0)
            {
                int mode = numbers[0] % 3;

                switch (mode)
                {
                    case 0:
                        totalSum += 10;
                        break;
                    case 1:
                        totalSum += 20;
                        break;
                    case 2:
                        totalSum += 30;
                        break;
                    case 3:
                        totalSum += 40;
                        break;
                    default:
                        totalSum += 0;
                        break;
                }
            }
            else if (numbers.Count == 0)
            {
                totalSum = -1;
            }
            else
            {
                totalSum = -2;
            }

            int k = 0;
            while (k < numbers.Count)
            {
                totalSum += (numbers[k] > 5) ? 2 : 1;
                k++;
            }

            int limit = 3;
            do
            {
                totalSum += limit;
                limit--;
            } while (limit > 0);

            foreach (int item in numbers)
            {
                if (item % 2 == 0)
                {
                    totalSum += item;
                }
            }

            Console.WriteLine(totalSum);
        }
    }
}