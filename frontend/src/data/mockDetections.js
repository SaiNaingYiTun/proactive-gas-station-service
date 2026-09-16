export const currentDetection = {
  id: 1,
  customerId: 'C001',
  licensePlate: 'ABC-1234',
  vehicle: 'Toyota Camry',
  vehicleColor: 'Black',
  confidence: 96.8,
  status: 'Returning',
  detectedAt: '14:32:15',

  customer: {
    name: 'John Doe',
    preferredFuel: 'Gasohol 95',
    preferredPayment: 'Credit Card',
    carWash: 'Yes',
    totalVisits: 14,
    lastVisit: '18 Aug 2026',
  },
}

export const recentDetections = [
  {
    id: 1,
    licensePlate: 'ABC-1234',
    customer: 'John Doe',
    vehicle: 'Toyota Camry',
    time: '14:32',
    status: 'Returning',
  },
  {
    id: 2,
    licensePlate: '7กข-5544',
    customer: 'Unknown',
    vehicle: 'Honda Civic',
    time: '14:27',
    status: 'New',
  },
  {
    id: 3,
    licensePlate: 'XYZ-8923',
    customer: 'Sarah Lee',
    vehicle: 'Mazda 3',
    time: '14:19',
    status: 'Returning',
  },
  {
    id: 4,
    licensePlate: '9กม-2811',
    customer: 'Michael Tan',
    vehicle: 'Toyota Fortuner',
    time: '14:08',
    status: 'Returning',
  },
]