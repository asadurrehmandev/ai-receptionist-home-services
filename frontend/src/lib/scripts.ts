export type CallerScript = {
  id: string;
  label: string;
  detail: string;
  turns: string[];
};

export const SCRIPTS: CallerScript[] = [
  {
    id: "drain",
    label: "Book a drain call",
    detail: "Kitchen backup · Jordan Hale in 78704",
    turns: [
      "My kitchen drain is clogged and backing up into the sink.",
      "Jordan Hale",
      "512-555-0164",
      "880 West Mary Street, Austin 78704",
      "the earliest you have",
      "yes",
    ],
  },
  {
    id: "gas",
    label: "Gas smell",
    detail: "Transfers to the on-call technician",
    turns: [
      "I smell gas in the laundry room at 18 Rio Grande Street, Austin 78701. I'm Chris Patel, 512-555-0108.",
    ],
  },
  {
    id: "burst",
    label: "Burst pipe",
    detail: "Active flooding · emergency dispatch",
    turns: [
      "My pipe burst at 1402 Manor Road, Austin 78702 and water is everywhere. I'm Lena Ortiz, 512-555-0177.",
    ],
  },
  {
    id: "quote",
    label: "Price a water heater",
    detail: "Gives a range, then the caller declines",
    turns: ["How much does a water heater replacement cost?", "no thanks"],
  },
  {
    id: "spam",
    label: "Sales call",
    detail: "SEO pitch · closed as spam",
    turns: ["Hi, we help plumbers rank on Google and improve their SEO listings."],
  },
  {
    id: "reschedule",
    label: "Move Dana's visit",
    detail: "Last four digits and the visit day, then a clear yes",
    turns: [
      "Hi this is Dana Cho, I need to reschedule my appointment to the earliest you have.",
      "0133 Thursday",
      "yes",
    ],
  },
];
