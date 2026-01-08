import React from 'react';
import { Link } from "react-router-dom";

import { useAuth } from '../hooks/useAuth';
import { getCSRFToken } from "../utils/csrf";


export function Footer() {
    return (
        <footer className="bg-gray-800 py-8">
            <div className="container mx-auto px-4 text-center text-white">
                <p>&copy; 2025 <a href="https://www.mokkapi.com">Mokkapi</a>. All rights reserved.</p>
            </div>
        </footer>
    )
}