import React from 'react';
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from '../hooks/useAuth';
import { getCSRFToken } from "../utils/csrf";

import logo from '../../images/logo.png';

export function  Navbar() {


    const { user, setUser } = useAuth();
    const navigate = useNavigate();

    const handleLogout = async () => {
        const csrftoken = getCSRFToken();
        await fetch("/logout/", {
        method: "POST",
        credentials: "include",
        headers: {
            "X-CSRFToken": csrftoken || "",
            "Content-Type": "application/json",
        },
        });
        // Clear client state & bounce to login (or home)
        setUser({ is_authenticated: false, is_staff: false, username: "" });
        navigate("/");
    };

    if (!user) return null;

    return (
        <nav className="bg-white shadow">
            <div className="container mx-auto px-4">
                <div className="flex justify-between items-center py-4">
                    <div>
                        <a href="#" className="flex items-center">
                            <img className="logo-navbar" src={logo} alt="Mokkapi logo, an M within curly brackets" />
                            <span className="text-xl font-bold text-gray-800 ml-2">Mokkapi</span>
                        </a>
                    </div>
                    <div>
                    {user.is_authenticated ? (
                        <>
                        <Link to="/" className="mx-2 hover:text-gray-800">Home</Link>
                        {user.is_staff && (
                            <Link to="/admin" className="mx-2 hover:text-gray-800">Admin</Link>
                        )}
                        <button
                            onClick={handleLogout}
                            className="mx-2 hover:text-gray-800 bg-none border-none cursor-pointer"
                        >
                            Logout
                        </button>
                        </>
                    ) : (
                        <Link to={"/login"} className="mx-2 hover:text-gray-800">Login</Link>
                    ) }
                    </div>
                </div>
            </div>
        </nav>
    );
}