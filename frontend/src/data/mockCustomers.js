export const customers = [
  {
    id: 'C001',
    name: 'John Doe',
    phone: '081-234-5678',
    email: 'john.doe@email.com',
    status: 'Returning',
    totalVisits: 14,
    lastVisit: '18 Aug 2026',

    vehicle: {
      licensePlate: 'ABC-1234',
      make: 'Toyota',
      model: 'Camry',
      color: 'Black',
    },

    preferences: {
      fuel: 'Gasohol 95',
      payment: 'Credit Card',
      carWash: 'Yes',
      favoriteService: 'Full Service Refuel',
    },

    purchaseHistory: [
      {
        id: 1,
        date: '18 Aug 2026',
        fuel: 'Gasohol 95',
        amount: 1500,
        payment: 'Credit Card',
      },
      {
        id: 2,
        date: '10 Aug 2026',
        fuel: 'Gasohol 95',
        amount: 1200,
        payment: 'Credit Card',
      },
      {
        id: 3,
        date: '02 Aug 2026',
        fuel: 'Gasohol 95',
        amount: 1400,
        payment: 'Credit Card',
      },
    ],

    incidents: [],
  },

  {
    id: 'C002',
    name: 'Sarah Lee',
    phone: '089-555-2244',
    email: 'sarah.lee@email.com',
    status: 'Returning',
    totalVisits: 8,
    lastVisit: '17 Aug 2026',

    vehicle: {
      licensePlate: 'XYZ-8923',
      make: 'Mazda',
      model: '3',
      color: 'White',
    },

    preferences: {
      fuel: 'Gasohol 91',
      payment: 'QR Payment',
      carWash: 'No',
      favoriteService: 'Quick Refuel',
    },

    purchaseHistory: [
      {
        id: 1,
        date: '17 Aug 2026',
        fuel: 'Gasohol 91',
        amount: 900,
        payment: 'QR Payment',
      },
      {
        id: 2,
        date: '08 Aug 2026',
        fuel: 'Gasohol 91',
        amount: 1100,
        payment: 'QR Payment',
      },
    ],

    incidents: [
      {
        id: 'INC-002',
        date: '08 Aug 2026',
        type: 'Payment Issue',
        status: 'Open',
        note: 'Customer reported a duplicate payment notification.',
      },
    ],
  },

  {
    id: 'C003',
    name: 'Michael Tan',
    phone: '086-777-1188',
    email: 'michael.tan@email.com',
    status: 'Returning',
    totalVisits: 21,
    lastVisit: '16 Aug 2026',

    vehicle: {
      licensePlate: '9กม-2811',
      make: 'Toyota',
      model: 'Fortuner',
      color: 'Silver',
    },

    preferences: {
      fuel: 'Diesel',
      payment: 'Cash',
      carWash: 'Yes',
      favoriteService: 'Car Wash',
    },

    purchaseHistory: [
      {
        id: 1,
        date: '16 Aug 2026',
        fuel: 'Diesel',
        amount: 1800,
        payment: 'Cash',
      },
      {
        id: 2,
        date: '05 Aug 2026',
        fuel: 'Diesel',
        amount: 1700,
        payment: 'Cash',
      },
    ],

    incidents: [],
  },
]