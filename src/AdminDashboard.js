import React, { useState, useEffect } from "react";
import { Card, Col, Row, Tabs, Calendar, Button, Drawer, Typography, Spin } from "antd"; // Import Spin
import dayjs from "dayjs";
import { toast } from "sonner";
import axios from "axios"; // Import axios

const { TabPane } = Tabs;
const { Title, Text } = Typography;

// Component to display heatmap - you'll need to create this
// Based on previous discussion, this will take heatmap_data (list of points)
// and video_dimensions to draw on a court image.
import HeatmapDisplay from './HeatmapDisplay'; // <--- CREATE THIS COMPONENT

// Base URL for your Flask backend
const API_BASE_URL = 'http://127.0.0.1:5000/api'; // Adjust if your Flask app runs on a different port/host

const COURTS = ["Court 1", "Court 2"];

// Define mock data structure - adjust based on your backend's /api/courts response
const mockData = [
  {
    id: "court_1", // Added ID for mapping
    name: "Court 1",
    time_slots: [
       // Ensure these match the structure from your backend's /api/courts mock
       {"id": "slot_c1_9am", "time": "09:00", "status": "booked", "session_id": "sess_xyz_mock_court1_9am", "is_past": true, "bookedBy": "John Doe", "cost": 10, "startHour": 9},
       {"id": "slot_c1_10am", "time": "10:00", "status": "booked", "session_id": "sess_abc_mock_court1_10am", "is_past": true, "bookedBy": "Jane Smith", "cost": 10, "startHour": 10},
       {"id": "slot_c1_11am", "time": "11:00", "status": "booked", "session_id": "sess_def_mock_court1_11am", "is_past": false, "bookedBy": "Alice King", "cost": 10, "startHour": 11},
       {"id": "slot_c1_12pm", "time": "12:00", "status": "available", "session_id": null, "is_past": false},
       {"id": "slot_c1_8am", "time": "08:00", "status": "available", "session_id": null, "is_past": false},
    ]
  },
  {
     id: "court_2",
     name: "Court 2",
     time_slots: [
        {"id": "slot_c2_9am", "time": "09:00", "status": "booked", "session_id": "sess_ghi_mock_court2_9am", "is_past": true, "bookedBy": "Bob Lee", "cost": 10, "startHour": 9},
        {"id": "slot_c2_10am", "time": "10:00", "status": "available", "session_id": null, "is_past": false},
     ]
  }
];


const AdminDashboard = () => {
  const [courts, setCourts] = useState([]); // State to hold court data from backend
  const [selectedCourtKey, setSelectedCourtKey] = useState("Court 1"); // Use key for Tabs
  const [selectedDate, setSelectedDate] = useState(dayjs()); // Not used by mock backend yet, but good practice
  const [expandedSlotIndex, setExpandedSlotIndex] = useState(null); // Use index to track expanded card
  const [analysisDrawerOpen, setAnalysisDrawerOpen] = useState(false);
  const [analysisSessionId, setAnalysisSessionId] = useState(null); // Store which session is being analyzed

  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState({}); // State to track if analysis is pending for a session_id {session_id: true/false}


  const fetchCourts = async () => {
    try {
      // Replace mock data with actual backend call
      // const response = await axios.get(`${API_BASE_URL}/courts`);
      // setCourts(response.data);
      setCourts(mockData); // Use mock data for now
      toast.success("Court data loaded successfully");
    } catch (err) {
      console.error("Error fetching courts:", err);
      toast.error("Failed to load court data");
    }
  };

  useEffect(() => {
    fetchCourts();
    // In a real app, filtering by date/court would happen on the backend
  }, [selectedCourtKey, selectedDate]); // Re-fetch if court or date changes

  const currentHour = new Date().getHours(); // Simple hour check

  const handleAnalyzeBooking = async (slot) => {
      if (!slot.session_id) {
          toast.error("Session ID is missing for this booking.");
          return;
      }
       if (isAnalyzing[slot.session_id]) {
           toast("Analysis is already in progress for this session.");
           return;
       }


      setAnalysisSessionId(slot.session_id);
      setAnalysisDrawerOpen(true); // Open drawer immediately
      setAnalysisLoading(true);
      setAnalysisData(null); // Clear previous data
      setAnalysisError(null);
      setIsAnalyzing(prevState => ({...prevState, [slot.session_id]: true}));


      try {
          // --- Step 1: Trigger Analysis on Backend ---
          // The backend endpoint will run the script and save results.
          // We configured the backend to wait for the script to finish before responding.
          const triggerResponse = await axios.post(`${API_BASE_URL}/analyze_booking/${slot.session_id}`);
          toast.success(triggerResponse.data.message || "Analysis triggered successfully.");

          // --- Step 2: Fetch Results from Backend ---
          // Since backend waits, results should be available immediately after trigger success.
          const resultsResponse = await axios.get(`${API_BASE_URL}/analysis_results/${slot.session_id}`);
          setAnalysisData(resultsResponse.data); // Set the fetched analysis data


      } catch (err) {
          console.error("Error during analysis process:", err);
          const errorMessage = err.response?.data?.error || err.message || "An unknown error occurred during analysis.";
          setAnalysisError(errorMessage);
          toast.error(`Analysis failed: ${errorMessage}`);
      } finally {
          setAnalysisLoading(false);
          setIsAnalyzing(prevState => ({...prevState, [slot.session_id]: false}));
      }
  };


  const handleCardClick = (index, slot) => {
      // Expand/collapse card
      const newExpandedIndex = index === expandedSlotIndex ? null : index;
      setExpandedSlotIndex(newExpandedIndex);

      // If expanding a past/booked slot, potentially fetch preliminary info or just wait for analyze click
      // If collapsing, clear any active analysis state related to this card if needed
      if (newExpandedIndex === null) {
          // Optional: if drawer is open for this slot, close it
          if (analysisSessionId === slot.session_id) {
             setAnalysisDrawerOpen(false);
             setAnalysisSessionId(null);
          }
      }
  };

  const handleDrawerClose = () => {
      setAnalysisDrawerOpen(false);
      setAnalysisSessionId(null); // Clear session ID when closing drawer
      setAnalysisData(null); // Clear analysis data
      setAnalysisError(null); // Clear error
      // Don't clear isAnalyzing status immediately, backend might still be working if it was triggered
  };

   // Find the currently selected court data
   const selectedCourtData = courts.find(court => court.name === selectedCourtKey);


  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>Admin Dashboard</Title>
      {/* Use court ID or a stable key if possible for Tabs */}
      <Tabs activeKey={selectedCourtKey} onChange={setSelectedCourtKey} style={{ marginBottom: 16 }}>
        {courts.map(court => (
          <TabPane tab={<span>{court.name}</span>} key={court.name} />
        ))}
      </Tabs>

      {/* Optional: Calendar for selecting date - integrate with backend fetch if needed */}
      {/* <Calendar fullscreen={false} value={selectedDate} onSelect={setSelectedDate} style={{ marginBottom: 24 }} /> */}

       {selectedCourtData ? (
           <Row gutter={[16, 16]}>
            {selectedCourtData.time_slots
               .sort((a, b) => a.startHour - b.startHour) // Sort by start hour
               .map((slot, index) => {
              // Determine if analyze button should show
              const showAnalyzeButton = slot.status === "Booked" && slot.is_past && slot.session_id;
              const isExpanded = expandedSlotIndex === index;
              // Simple check if the start time is before the current hour
              const slotStartTime = dayjs(selectedDate).hour(slot.startHour).minute(0).second(0);
              const now = dayjs();
              const isElapsed = slotStartTime.isBefore(now);


              return (
                <Col key={slot.id} xs={24} sm={12} md={8} lg={6}> {/* Responsive column sizing */}
                  <Card
                    hoverable
                    style={{
                      backgroundColor: slot.status === "Booked" ? "#e6fffb" : "#f6ffed", // Booked: Light Blue, Available: Light Green
                      border: isExpanded ? "2px solid #1890ff" : undefined, // Ant Design Primary Blue border
                      minHeight: 150, // Ensure minimum height for consistency
                      display: 'flex', // Use flex for content layout
                      flexDirection: 'column',
                      justifyContent: 'space-between' // Space out content
                    }}
                     // Changed onClick to handleCardClick
                    onClick={() => handleCardClick(index, slot)}
                  >
                    <div> {/* Content area */}
                      <Title level={5} style={{ marginBottom: 8 }}>{slot.time || `${slot.startHour}:00 - ${slot.startHour + 1}:00`}</Title> {/* Use slot.time or construct */}
                      <Text type="secondary" style={{marginBottom: 4, display: 'block'}}>Status: <span style={{ fontWeight: 'bold', color: slot.status === 'Booked' ? '#08979c' : '#73d13d' }}>{slot.status}</span></Text>
                      {slot.status === "Booked" && (
                          <>
                            <Text type="secondary" style={{marginBottom: 4, display: 'block'}}>Booked by: {slot.bookedBy || "-"}</Text>
                            <Text type="secondary" style={{marginBottom: 4, display: 'block'}}>Cost: Rs. {slot.cost ? slot.cost.toFixed(2) : "-"}</Text>
                          </>
                      )}
                    </div>


                    {isExpanded && showAnalyzeButton && (
                      <Button
                        type="primary"
                        block
                        style={{ marginTop: 12 }}
                        onClick={(e) => {
                            e.stopPropagation(); // Prevent card click from collapsing when button is clicked
                            handleAnalyzeBooking(slot);
                        }}
                        loading={isAnalyzing[slot.session_id]} // Show loading on button
                      >
                       {isAnalyzing[slot.session_id] ? 'Analyzing...' : 'Analyze Booking'}
                      </Button>
                    )}
                    {/* Optional: Display a status message for past booked slots without analysis button */}
                    {isExpanded && slot.status === "Booked" && slot.is_past && !showAnalyzeButton && (
                         <Text type="secondary" style={{ marginTop: 12, display: 'block' }}>Analysis unavailable or not applicable.</Text>
                    )}
                     {isExpanded && slot.status === "Booked" && !slot.is_past && (
                          <Text type="secondary" style={{ marginTop: 12, display: 'block' }}>Ongoing or Upcoming Booking.</Text>
                     )}
                  </Card>
                </Col>
              );
            })}
          </Row>
       ) : (
           <div style={{textAlign: 'center', padding: '40px 0'}}>
               <Text type="secondary">Select a court or no data available.</Text>
           </div>
       )}


      <Drawer
        title="Booking Analysis"
        placement="right"
        onClose={handleDrawerClose}
        open={analysisDrawerOpen}
        width={720} // Adjust drawer width
        destroyOnClose={true} // Clean up components inside on close
      >
        {analysisLoading ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>
               <Spin size="large" />
               <Title level={4} style={{marginTop: 16}}>Analyzing video...</Title>
               <Text type="secondary">This may take a few minutes.</Text>
            </div>
        ) : analysisError ? (
            <div style={{ color: 'red', textAlign: 'center', padding: '20px' }}>
               <Title level={4} type="danger">Analysis Failed</Title>
               <Text>{analysisError}</Text>
               <p style={{marginTop: 16}}>Please check the backend logs for details.</p>
            </div>
        ) : analysisData ? (
            <div>
                <Title level={4}>Analysis Results for Session {analysisSessionId}</Title>
                {/* Display Analysis Data */}
                <Card style={{marginBottom: 24}}>
                    <Title level={5}>Summary</Title>
                    <p>Total Shots Detected: <Text strong>{analysisData.total_shots}</Text></p>
                    {/* Add other summary stats here if available */}
                </Card>

                <Card>
                     <Title level={5}>Player Position Heatmap</Title>
                     {/* Pass heatmap_data and video_dimensions to HeatmapDisplay */}
                     {analysisData.heatmap_data && analysisData.video_dimensions ? (
                         <HeatmapDisplay
                             playerPositions={analysisData.heatmap_data} // List of {x, y, conf}
                             videoDimensions={analysisData.video_dimensions} // {width, height}
                         />
                     ) : (
                         <Text type="secondary">No player position data available for heatmap.</Text>
                     )}
                </Card>

            </div>
        ) : (
             <div style={{ textAlign: 'center', padding: '20px' }}>
                <Text type="secondary">Select a past booking and click "Analyze Booking" to view results.</Text>
             </div>
        )}
      </Drawer>
    </div>
  );
};

export default AdminDashboard;